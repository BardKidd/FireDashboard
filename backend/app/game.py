"""Phase 2: share-collecting mode (收集冊).

The view is share-based, not value-based: how many shares of each holding
have been collected, how close each one is to its next milestone and to its
share of the Coast (or FIRE) basket, and whether today's price is a "sale"
versus the 60-day average or 52-week high.

On top of that sits a small, forgiving game loop:

- Daily check-in (Taiwan date) earns stars. Streaks are counted in weeks,
  so missing a day never breaks anything.
- Badges unlock for share milestones (TW counted in 張), Coast progress,
  check-in counts, week streaks and every dividend received.
- Unlocked badges are stored and never revoked. Stars only go down when the
  user spends them on rewards they defined themselves. Levels use total
  stars ever earned, so spending never lowers the level.
- Levels unlock titles and accent-colour themes.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import calculator, ledger, loans
from .models import (
    Achievement,
    Checkin,
    Dividend,
    GameSettings,
    Holding,
    Loan,
    PortfolioSnapshot,
    Redemption,
    Reward,
    ShareLog,
    get_config,
)

EPS = 1e-6
CHECKIN_POINTS = 10

# Thresholds in shares. TW counts in 張 (1000 shares) from the first lot on;
# two odd-lot steps come first so odd-lot collecting has something to aim at.
MILESTONES = {
    "TW": [100, 500] + [n * 1000 for n in (1, 2, 3, 5, 10, 20, 30, 50, 100, 200, 300, 500, 1000)],
    "US": [1, 5, 10, 20, 50, 100, 200, 300, 500, 1000, 2000, 5000, 10000],
}
UNIT = {"TW": 1000.0, "US": 1.0}
UNIT_LABEL = {"TW": "張", "US": "股"}

CHECKIN_BADGES = {1: 20, 7: 50, 30: 150, 100: 300, 200: 500, 365: 1000, 500: 1000, 1000: 2000}
STREAK_BADGES = {4: 80, 12: 200, 26: 400, 52: 1000, 104: 2000}
COAST_STEPS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
DIVIDEND_POINTS = 20
FIRST_SHARE_POINTS = 20

TITLES = [
    (1, "播種新手"),
    (3, "小小收藏家"),
    (5, "定投園丁"),
    (8, "股息農夫"),
    (12, "複利工匠"),
    (16, "長期主義者"),
    (20, "雪球大師"),
    (30, "時間的朋友"),
]

# key, name, level needed, accent, accent-soft
THEMES = [
    ("ember", "營火", 1, "#f59e4b", "#4a2410"),
    ("teal", "青綠", 1, "#2dd4bf", "#134e4a"),
    ("orange", "暖陽", 3, "#fb923c", "#7c2d12"),
    ("violet", "暮紫", 5, "#a78bfa", "#4c1d95"),
    ("sky", "晴空", 8, "#38bdf8", "#0c4a6e"),
    ("rose", "櫻花", 12, "#fb7185", "#881337"),
    ("lime", "新芽", 16, "#a3e635", "#365314"),
    ("gold", "金色", 20, "#facc15", "#713f12"),
]

QUOTES = [
    "市場每天都在變，你的股數只會在你決定的時候改變。",
    "今天不需要做任何決定，打卡就算完成。",
    "複利最需要的是時間，而時間你每天都在累積。",
    "下跌的日子，同樣的錢能收集更多股數。",
    "把注意力放在股數，而不是價格。",
    "慢慢來，比較快。",
    "長期投資的成果，多半來自那些什麼都沒做的日子。",
    "你已經在路上了。",
    "看完就去過生活吧，市場會自己運作。",
    "存下來的每一股，都在替未來的你工作。",
    "不用每天進步，只要不後退就很好。",
    "價格是別人給的，股數是你自己收集的。",
]


class GameError(ValueError):
    pass


# ------------------------------------------------------------------ levels

def level_threshold(level: int) -> int:
    """Total stars needed to reach a level: 0, 100, 300, 600, 1000, ..."""
    return 50 * (level - 1) * level


def level_for(xp: int) -> int:
    lv = 1
    while level_threshold(lv + 1) <= xp:
        lv += 1
    return lv


def title_for(level: int) -> str:
    return [t for need, t in TITLES if level >= need][-1]


def next_title(level: int) -> tuple[int, str] | None:
    for need, t in TITLES:
        if need > level:
            return need, t
    return None


# ------------------------------------------------------------------ share history

@dataclass
class SharePoint:
    date: str
    shares: float  # in today's (post-split) share units


def _adjusted_logs(db: Session, symbol: str) -> tuple[list[SharePoint], list[dict]]:
    """Share totals restated in post-split units, so a split is not a jump.

    Returns (end-of-day curve, user events with notes)."""
    logs = ledger._logs(db, symbol)
    splits = [(l.date, l.split_ratio or 1.0) for l in logs if l.kind == "split"]

    def factor(d: str) -> float:
        f = 1.0
        for sd, r in splits:
            if sd > d:
                f *= r
        return f

    curve: list[SharePoint] = []
    events: list[dict] = []
    for l in logs:
        if l.kind == "split":
            continue
        f = factor(l.date)
        total = l.total_shares_after * f
        if curve and curve[-1].date == l.date:
            curve[-1].shares = total
        else:
            curve.append(SharePoint(l.date, total))
        events.append(
            {
                "date": l.date,
                "kind": l.kind,
                "delta": l.delta_shares * f,
                "total": total,
                "note": l.note,
            }
        )
    return curve, events


def _first_reach(curve: list[SharePoint], amount: float) -> str | None:
    for p in curve:
        if p.shares >= amount - EPS:
            return p.date
    return None


def _milestone_market(h: Holding) -> str | None:
    return h.market if h.market in MILESTONES else None


def milestone_label(n: float, market: str) -> str:
    if market == "TW" and n >= 1000:
        return f"{n / 1000:g} 張"
    return f"{n:g} 股"


def fmt_units(shares: float, market: str) -> str:
    if market == "TW":
        lots = shares / 1000
        return f"{lots:g} 張" if abs(lots - round(lots)) < EPS else f"{shares:,.0f} 股"
    return f"{shares:g} 股"


# ------------------------------------------------------------------ candidates

def _candidates(db: Session) -> list[Achievement]:
    out: list[Achievement] = []
    stocks = list(db.scalars(select(Holding).where(Holding.market.in_(list(MILESTONES)))))
    for h in stocks:
        m = _milestone_market(h)
        curve, _ = _adjusted_logs(db, h.symbol)
        label = h.symbol.replace(".TWO", "").replace(".TW", "")
        first = _first_reach(curve, EPS * 10)
        if first:
            out.append(
                Achievement(
                    key=f"first:{h.symbol}", category="first", symbol=h.symbol,
                    title=f"收藏 {label}", detail="收集到第一股", earned_on=first,
                    points=FIRST_SHARE_POINTS,
                )
            )
        for i, n in enumerate(MILESTONES[m]):
            d = _first_reach(curve, n)
            if d is None:
                break
            out.append(
                Achievement(
                    key=f"ms:{h.symbol}:{n}", category="milestone", symbol=h.symbol,
                    title=f"{label} {milestone_label(n, m)}", detail=f"Lv.{i + 1}",
                    earned_on=d, points=50 + 25 * i,
                )
            )

    reached: set[int] = set()
    all_loans = list(db.scalars(select(Loan)))
    for s in db.scalars(select(PortfolioSnapshot).order_by(PortfolioSnapshot.date)):
        if not s.coast_target_twd:
            continue
        net = s.total_value_twd - loans.total_on(all_loans, date.fromisoformat(s.date))
        pct = net / s.coast_target_twd * 100
        for step in COAST_STEPS:
            if step not in reached and pct >= step:
                reached.add(step)
                out.append(
                    Achievement(
                        key=f"coast:{step}", category="coast",
                        title="抵達 Coast FIRE" if step == 100 else f"Coast 進度 {step}%",
                        detail="從此不再投入也能準時退休" if step == 100 else None,
                        earned_on=s.date, points=500 if step == 100 else 100,
                    )
                )

    days = [c.date for c in db.scalars(select(Checkin).order_by(Checkin.date))]
    for n, pts in CHECKIN_BADGES.items():
        if len(days) >= n:
            out.append(
                Achievement(
                    key=f"checkin:{n}", category="checkin",
                    title="第一次打卡" if n == 1 else f"累積打卡 {n} 天",
                    earned_on=days[n - 1], points=pts,
                )
            )
    run, prev = 0, None
    for d in days:
        monday = _monday(d)
        if monday == prev:
            continue
        run = run + 1 if prev is not None and monday == prev + timedelta(days=7) else 1
        prev = monday
        if run in STREAK_BADGES:
            out.append(
                Achievement(
                    key=f"streak:{run}", category="streak", title=f"連續 {run} 週打卡",
                    earned_on=d, points=STREAK_BADGES[run],
                )
            )

    names = {h.symbol: h.symbol.replace(".TWO", "").replace(".TW", "") for h in stocks}
    for dv in db.scalars(select(Dividend)):
        out.append(
            Achievement(
                key=f"div:{dv.symbol}:{dv.ex_date}", category="dividend", symbol=dv.symbol,
                title=f"領到 {names.get(dv.symbol, dv.symbol)} 股息",
                detail=f"{dv.net:,.2f} {dv.currency}", earned_on=dv.ex_date,
                points=DIVIDEND_POINTS,
            )
        )
    return out


def sync(db: Session) -> list[Achievement]:
    """Add newly earned achievements. Existing ones are never removed."""
    have = set(db.scalars(select(Achievement.key)))
    new = []
    for a in _candidates(db):
        if a.key not in have:
            have.add(a.key)
            db.add(a)
            new.append(a)
    db.flush()
    return new


# ------------------------------------------------------------------ check-in

def _monday(d: str) -> date:
    x = date.fromisoformat(d)
    return x - timedelta(days=x.weekday())


def week_streak(days: list[str], today: date) -> int:
    """Consecutive weeks with a check-in. The current week doesn't break the
    streak until it's over, so there's always until Sunday to keep it."""
    weeks = sorted({_monday(d) for d in days}, reverse=True)
    if not weeks:
        return 0
    this_week = today - timedelta(days=today.weekday())
    if weeks[0] < this_week - timedelta(days=7):
        return 0
    run = 1
    for a, b in zip(weeks, weeks[1:]):
        if a - b == timedelta(days=7):
            run += 1
        else:
            break
    return run


def quote_for(day: date) -> str:
    h = int(hashlib.md5(day.isoformat().encode()).hexdigest(), 16)
    return QUOTES[h % len(QUOTES)]


def checkin(db: Session, note: str | None = None, today: date | None = None) -> dict:
    today = today or ledger.today_tw()
    d = today.isoformat()
    if db.get(Checkin, d) is not None:
        raise GameError("今天已經打過卡了")
    prev = db.scalar(select(Checkin).order_by(Checkin.date.desc()))
    db.add(Checkin(date=d, points=CHECKIN_POINTS, note=(note or "").strip() or None))
    db.flush()
    new = sync(db)

    since = prev.date if prev else None
    collected = []
    if since:
        q = (
            select(ShareLog.symbol, func.sum(ShareLog.delta_shares))
            .where(ShareLog.date > since, ShareLog.kind.in_(["buy", "sell", "adjust"]))
            .group_by(ShareLog.symbol)
        )
        for sym, delta in db.execute(q):
            h = db.get(Holding, sym)
            if h is not None and abs(delta) > EPS and h.market in MILESTONES:
                collected.append({"symbol": sym, "delta": delta, "market": h.market})

    view = collect_view(db, today)
    bargains = [
        {"symbol": r["symbol"], "label": r["label"], "extra": r["radar"]["extra_vs_ma60"]}
        for r in view["holdings"]
        if r["radar"] and (r["radar"]["extra_vs_ma60"] or 0) > 0.005
    ]
    bargains.sort(key=lambda b: -b["extra"])
    days = [c for c in db.scalars(select(Checkin.date))]
    return {
        "date": d,
        "points": CHECKIN_POINTS,
        "bonus": sum(a.points for a in new),
        "new_achievements": [_ach_dict(a) for a in new],
        "total_days": len(days),
        "week_streak": week_streak(days, today),
        "since": since,
        "collected": collected,
        "bargains": bargains[:3],
        "quote": quote_for(today),
    }


# ------------------------------------------------------------------ collection view

def _settings(db: Session) -> GameSettings:
    s = db.get(GameSettings, 1)
    if s is None:
        s = GameSettings(id=1)
        db.add(s)
        db.flush()
    return s


def _radar(price: float | None, ma60: float | None, high: float | None) -> dict | None:
    if not price:
        return None

    def calc(ref: float | None):
        if not ref:
            return None, None
        return 1 - price / ref, ref / price - 1

    d60, e60 = calc(ma60)
    dh, eh = calc(high)
    return {
        "price": price, "ma60": ma60, "high_52w": high,
        "discount_vs_ma60": d60, "extra_vs_ma60": e60,
        "discount_vs_high": dh, "extra_vs_high": eh,
    }


def collect_view(db: Session, today: date | None = None) -> dict:
    today = today or ledger.today_tw()
    cfg = get_config(db)
    settings = _settings(db)
    pos = ledger.position_rows(db, cfg)
    params = calculator.FireParams.from_config(cfg)
    coast0 = calculator.coast_target(params, calculator.months_remaining(params, today))
    fire = calculator.fire_target(params)
    goal = fire if settings.basket_goal == "fire" else coast0
    # Loans are paid back out of these holdings' net worth, so the basket has
    # to hold the goal plus what is still owed.
    debt = loans.total_on(list(db.scalars(select(Loan))), today)
    fx = pos["fx"]["used"]
    total = pos["total_twd"]
    holdings_by_sym = {h.symbol: h for h in db.scalars(select(Holding))}

    rows = []
    basket_have = basket_need = 0.0
    for r in pos["rows"]:
        if r["market"] not in MILESTONES:
            continue
        if r["archived"] and r["shares"] <= EPS:
            continue
        m = r["market"]
        sym = r["symbol"]
        h = holdings_by_sym[sym]
        curve, events = _adjusted_logs(db, sym)
        shares_now = r["shares"]
        unit = UNIT[m]
        ladder = MILESTONES[m]
        level = sum(1 for n in ladder if shares_now >= n - EPS)
        nxt = ladder[level] if level < len(ladder) else None
        prev_amt = ladder[level - 1] if level else 0.0
        to_next = None
        if nxt is not None:
            to_next = (shares_now - prev_amt) / (nxt - prev_amt)

        base = r["ma200"] or r["price"]
        rate = fx if r["currency"] == "USD" else 1.0
        base_twd = base * rate if base and rate else None
        weight = (r["value_twd"] or 0) / total if total > 0 else 0
        auto_target = (goal + debt) * weight / base_twd if base_twd and weight > 0 else None
        target = h.target_shares or auto_target
        target_progress = shares_now / target if target else None
        if target and base_twd:
            basket_need += target * base_twd
            basket_have += min(shares_now, target) * base_twd

        first = curve[0].date if curve else None
        rows.append(
            {
                "symbol": sym,
                "label": sym.replace(".TWO", "").replace(".TW", ""),
                "name": r["name"],
                "market": m,
                "asset_type": r["asset_type"],
                "shares": shares_now,
                "unit": unit,
                "unit_label": UNIT_LABEL[m],
                "level": level,
                "max_level": len(ladder),
                "next_milestone": nxt,
                "next_label": milestone_label(nxt, m) if nxt is not None else None,
                "progress_to_next": to_next,
                "target_shares": target,
                "target_is_manual": bool(h.target_shares),
                "target_progress": target_progress,
                "base_price": base,
                "radar": _radar(r["price"], r["ma60"], r["high_52w"]),
                "first_date": first,
                "days_held": (today - date.fromisoformat(first)).days if first else 0,
                "curve": [{"date": p.date, "shares": p.shares} for p in curve],
                "events": events,
            }
        )
    rows.sort(key=lambda x: (-(x["target_progress"] or 0), x["symbol"]))
    return {
        "today": today.isoformat(),
        "basket_goal": settings.basket_goal,
        "goal_amount": goal,
        "debt": debt,
        "coast_target": coast0,
        "fire_target": fire,
        "basket_progress": basket_have / basket_need if basket_need else None,
        "holdings": rows,
    }


# ------------------------------------------------------------------ game state

def _ach_dict(a: Achievement) -> dict:
    return {
        "key": a.key, "category": a.category, "title": a.title, "detail": a.detail,
        "symbol": a.symbol, "earned_on": a.earned_on, "points": a.points,
    }


def balance(db: Session) -> tuple[int, int, int]:
    """(earned, spent, balance)."""
    earned = (db.scalar(select(func.sum(Checkin.points))) or 0) + (
        db.scalar(select(func.sum(Achievement.points))) or 0
    )
    spent = db.scalar(select(func.sum(Redemption.cost))) or 0
    return earned, spent, earned - spent


def _next_goals(db: Session, view: dict, total_days: int, streak: int) -> list[dict]:
    goals = []
    for n, pts in CHECKIN_BADGES.items():
        if total_days < n:
            goals.append(
                {"title": f"累積打卡 {n} 天", "progress": total_days / n,
                 "hint": f"還差 {n - total_days} 天", "points": pts}
            )
            break
    for n, pts in STREAK_BADGES.items():
        if streak < n:
            goals.append(
                {"title": f"連續 {n} 週打卡", "progress": streak / n,
                 "hint": "每週至少打卡一次", "points": pts}
            )
            break
    for r in view["holdings"]:
        if r["next_milestone"] is not None:
            need = r["next_milestone"] - r["shares"]
            goals.append(
                {
                    "title": f"{r['label']} {r['next_label']}",
                    "progress": r["shares"] / r["next_milestone"],
                    "hint": "還差 " + fmt_units(need, r["market"]),
                    "points": 50 + 25 * r["level"],
                }
            )
    have = set(db.scalars(select(Achievement.key).where(Achievement.category == "coast")))
    for step in COAST_STEPS:
        if f"coast:{step}" not in have:
            goals.append(
                {"title": "抵達 Coast FIRE" if step == 100 else f"Coast 進度 {step}%",
                 "progress": None, "hint": "以每日淨值計算", "points": 500 if step == 100 else 100}
            )
            break
    goals.sort(key=lambda g: -(g["progress"] if g["progress"] is not None else -1))
    return goals


def state(db: Session, today: date | None = None) -> dict:
    today = today or ledger.today_tw()
    sync(db)
    earned, spent, bal = balance(db)
    lv = level_for(earned)
    checkins = list(db.scalars(select(Checkin).order_by(Checkin.date)))
    days = [c.date for c in checkins]
    streak = week_streak(days, today)
    achievements = list(
        db.scalars(select(Achievement).order_by(Achievement.earned_on.desc(), Achievement.created_at.desc()))
    )
    settings = _settings(db)
    view = collect_view(db, today)
    rewards = list(db.scalars(select(Reward).where(Reward.archived.is_(False)).order_by(Reward.cost)))
    redemptions = list(db.scalars(select(Redemption).order_by(Redemption.date.desc(), Redemption.id.desc())))
    redeemed_ids = {r.reward_id for r in redemptions}
    nt = next_title(lv)
    today_row = db.get(Checkin, today.isoformat())
    return {
        "today": today.isoformat(),
        "stars": {"earned": earned, "spent": spent, "balance": bal},
        "level": {
            "level": lv,
            "title": title_for(lv),
            "xp": earned,
            "current_floor": level_threshold(lv),
            "next_at": level_threshold(lv + 1),
            "next_title": {"level": nt[0], "title": nt[1]} if nt else None,
        },
        "checkin": {
            "today": today_row is not None,
            "today_note": today_row.note if today_row else None,
            "total_days": len(days),
            "week_streak": streak,
            "days": days[-400:],
            "quote": quote_for(today),
        },
        "achievements": [_ach_dict(a) for a in achievements],
        "next_goals": _next_goals(db, view, len(days), streak)[:6],
        "themes": [
            {"key": k, "name": n, "level": need, "accent": a, "soft": s, "unlocked": lv >= need}
            for k, n, need, a, s in THEMES
        ],
        "settings": {"theme": settings.theme, "basket_goal": settings.basket_goal},
        "rewards": [
            {
                "id": r.id, "name": r.name, "cost": r.cost, "repeatable": r.repeatable,
                "note": r.note, "redeemed": r.id in redeemed_ids,
            }
            for r in rewards
        ],
        "redemptions": [
            {"id": r.id, "reward_id": r.reward_id, "name": r.name, "cost": r.cost, "date": r.date}
            for r in redemptions[:30]
        ],
    }


# ------------------------------------------------------------------ rewards

def redeem(db: Session, reward_id: int, today: date | None = None) -> Redemption:
    r = db.get(Reward, reward_id)
    if r is None or r.archived:
        raise GameError("找不到獎勵")
    if not r.repeatable and db.scalar(select(Redemption.id).where(Redemption.reward_id == r.id).limit(1)):
        raise GameError("這個獎勵只能兌換一次，已經兌換過了")
    _, _, bal = balance(db)
    if bal < r.cost:
        raise GameError(f"星星不夠：還差 {r.cost - bal} 顆")
    red = Redemption(reward_id=r.id, name=r.name, cost=r.cost, date=(today or ledger.today_tw()).isoformat())
    db.add(red)
    db.flush()
    return red


def set_settings(db: Session, theme: str | None, basket_goal: str | None) -> None:
    s = _settings(db)
    if theme is not None:
        lv = level_for(balance(db)[0])
        t = next((t for t in THEMES if t[0] == theme), None)
        if t is None:
            raise GameError("沒有這個主題")
        if lv < t[2]:
            raise GameError(f"「{t[1]}」主題在 Lv.{t[2]} 解鎖")
        s.theme = theme
    if basket_goal is not None:
        if basket_goal not in ("coast", "fire"):
            raise GameError("籃子目標只能是 coast 或 fire")
        s.basket_goal = basket_goal
    db.flush()
