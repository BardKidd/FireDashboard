"""Share ledger, dividends, quotes and snapshot rebuilding (SPEC.md 3 and 4).

Derived data is always rebuilt from source tables, so a backdated entry or a
newly detected split corrects the whole history.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import calculator, contracts
from .models import (
    CASH_SYMBOLS,
    CASH_TWD,
    CASH_USD,
    FX_SYMBOL,
    CorporateAction,
    Dividend,
    FireConfig,
    FixedContract,
    Holding,
    MarketQuote,
    PortfolioSnapshot,
    PriceHistory,
    ShareLog,
    get_config,
)

TZ = ZoneInfo("Asia/Taipei")
USER_KINDS = {"buy", "sell", "adjust", "deposit", "withdraw"}
EPS = 1e-9


class LedgerError(ValueError):
    pass


def today_tw() -> date:
    return datetime.now(TZ).date()


# ------------------------------------------------------------------ timelines

class Timeline:
    """Step function of shares (or cash) over dates."""

    def __init__(self, logs: list[ShareLog]):
        self.dates = [l.date for l in logs]
        self.totals = [l.total_shares_after for l in logs]

    def at(self, d: str) -> float:
        """Total at end of day d."""
        i = bisect_right(self.dates, d)
        return self.totals[i - 1] if i else 0.0

    def before(self, d: str) -> float:
        """Total at end of the day before d."""
        i = bisect_left(self.dates, d)
        return self.totals[i - 1] if i else 0.0


class PriceSeries:
    def __init__(self, rows: list[tuple[str, float]]):
        rows = sorted(rows)
        self.dates = [r[0] for r in rows]
        self.closes = [r[1] for r in rows]

    def __bool__(self) -> bool:
        return bool(self.dates)

    def on_or_before(self, d: str) -> float | None:
        i = bisect_right(self.dates, d)
        return self.closes[i - 1] if i else None

    def strictly_before(self, d: str) -> float | None:
        i = bisect_left(self.dates, d)
        return self.closes[i - 1] if i else None

    def mean_last(self, d: str, n: int) -> float | None:
        i = bisect_right(self.dates, d)
        if i < n:
            return None
        window = self.closes[i - n : i]
        return sum(window) / n

    def latest(self) -> tuple[str, float] | None:
        return (self.dates[-1], self.closes[-1]) if self.dates else None


def load_splits(db: Session) -> dict[str, list[tuple[str, float]]]:
    out: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for a in db.scalars(select(CorporateAction).where(CorporateAction.kind == "split")):
        if a.value and a.value != 1:
            out[a.symbol].append((a.date, a.value))
    return out


def split_factor(splits: list[tuple[str, float]], d: str) -> float:
    """Yahoo prices are split-adjusted: multiply by this to get the raw price on d."""
    f = 1.0
    for sd, r in splits:
        if sd > d:
            f *= r
    return f


def load_prices(db: Session, raw: bool = False) -> dict[str, PriceSeries]:
    """Adjusted series (for MAs, highs) or raw traded prices (for valuation)."""
    splits = load_splits(db) if raw else {}
    by_sym: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for sym, d, c in db.execute(select(PriceHistory.symbol, PriceHistory.date, PriceHistory.close)):
        f = split_factor(splits.get(sym, []), d) if raw else 1.0
        by_sym[sym].append((d, c * f))
    return {s: PriceSeries(r) for s, r in by_sym.items()}


def _logs(db: Session, symbol: str) -> list[ShareLog]:
    logs = list(db.scalars(select(ShareLog).where(ShareLog.symbol == symbol)))
    # A split takes effect at the start of its date, before that day's trades.
    logs.sort(key=lambda l: (l.date, 0 if l.kind == "split" else 1, l.id or 0))
    return logs


# ------------------------------------------------------------------ recompute

def recompute_symbol(db: Session, symbol: str) -> Timeline:
    logs = _logs(db, symbol)
    running = 0.0
    for log in logs:
        if log.kind == "split":
            log.delta_shares = running * ((log.split_ratio or 1.0) - 1)
        running += log.delta_shares
        if running < -EPS:
            raise LedgerError(f"{symbol} 在 {log.date} 的股數會變成負數（{running:g}）")
        running = max(running, 0.0) if abs(running) < EPS else running
        log.total_shares_after = running
    holding = db.get(Holding, symbol)
    if holding is not None:
        holding.shares = running
    db.flush()
    return Timeline(logs)


def ensure_split_logs(db: Session, symbol: str) -> None:
    existing = {
        l.date
        for l in db.scalars(
            select(ShareLog).where(ShareLog.symbol == symbol, ShareLog.kind == "split")
        )
    }
    for act in db.scalars(
        select(CorporateAction).where(
            CorporateAction.symbol == symbol, CorporateAction.kind == "split"
        )
    ):
        if act.date not in existing and act.value and act.value != 1:
            db.add(
                ShareLog(
                    date=act.date,
                    symbol=symbol,
                    kind="split",
                    split_ratio=act.value,
                    delta_shares=0.0,
                    note=f"股票分割 1 拆 {act.value:g}",
                )
            )
    db.flush()


def rebuild_dividends(db: Session, cfg: FireConfig, timelines: dict[str, Timeline]) -> None:
    db.execute(delete(Dividend))
    db.execute(delete(ShareLog).where(ShareLog.kind == "dividend"))
    db.flush()
    holdings = {h.symbol: h for h in db.scalars(select(Holding))}
    splits = load_splits(db)
    actions = db.scalars(
        select(CorporateAction).where(CorporateAction.kind == "dividend").order_by(CorporateAction.date)
    )
    for act in actions:
        h = holdings.get(act.symbol)
        tl = timelines.get(act.symbol)
        if h is None or tl is None:
            continue
        held = tl.before(act.date)
        if held <= EPS:
            continue
        per_share = act.value * split_factor(splits.get(act.symbol, []), act.date)
        gross = held * per_share
        tax = gross * cfg.us_dividend_tax if h.currency == "USD" else 0.0
        nhi = 0.0
        if h.currency == "TWD" and gross >= cfg.tw_nhi_threshold:
            nhi = gross * cfg.tw_nhi_rate
        net = gross - tax - nhi
        db.add(
            Dividend(
                symbol=act.symbol,
                ex_date=act.date,
                per_share=per_share,
                shares_held=held,
                gross=gross,
                tax_withheld=tax,
                nhi_premium=nhi,
                net=net,
                currency=h.currency,
            )
        )
        db.add(
            ShareLog(
                date=act.date,
                symbol=CASH_USD if h.currency == "USD" else CASH_TWD,
                kind="dividend",
                delta_shares=net,
                source_symbol=act.symbol,
                note=f"{act.symbol} 股息",
            )
        )
    db.flush()


def rebuild_quotes(db: Session, prices: dict[str, PriceSeries]) -> None:
    db.execute(delete(MarketQuote))
    for sym, ps in prices.items():
        latest = ps.latest()
        if latest is None:
            continue
        d, close = latest
        cutoff = (date.fromisoformat(d) - timedelta(days=365)).isoformat()
        i0 = bisect_left(ps.dates, cutoff)
        db.add(
            MarketQuote(
                symbol=sym,
                date=d,
                close=close,
                prev_close=ps.closes[-2] if len(ps.closes) > 1 else None,
                ma20=ps.mean_last(d, 20),
                ma60=ps.mean_last(d, 60),
                ma200=ps.mean_last(d, 200),
                high_52w=max(ps.closes[i0:]) if ps.closes[i0:] else None,
            )
        )
    db.flush()


def _business_days(start: date, end: date):
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def rebuild_snapshots(
    db: Session,
    cfg: FireConfig,
    timelines: dict[str, Timeline],
    prices: dict[str, PriceSeries],
    today: date | None = None,
) -> None:
    db.execute(delete(PortfolioSnapshot))
    today = today or today_tw()
    first = db.scalar(select(ShareLog.date).where(ShareLog.kind.in_(USER_KINDS)).order_by(ShareLog.date))
    if first is None:
        db.flush()
        return
    holdings = list(db.scalars(select(Holding)))
    fixed = [c for c in db.scalars(select(FixedContract)) if not c.closed]
    fx = prices.get(FX_SYMBOL, PriceSeries([]))
    params = calculator.FireParams.from_config(cfg)
    for day in _business_days(date.fromisoformat(first), today):
        d = day.isoformat()
        rate = fx.on_or_before(d)
        twd = usd = cash_twd = 0.0
        complete = True
        for h in holdings:
            tl = timelines.get(h.symbol)
            if tl is None:
                continue
            qty = tl.at(d)
            if abs(qty) < EPS:
                continue
            if h.market == "CASH":
                native = qty
            else:
                ps = prices.get(h.symbol)
                if not ps:
                    complete = False
                    continue
                # US close of day T belongs to the Taiwan snapshot of T+1.
                px = ps.strictly_before(d) if h.market == "US" else ps.on_or_before(d)
                if px is None:
                    px = ps.closes[0]  # holding predates fetched history
                native = qty * px
            if h.currency == "USD":
                if rate is None:
                    complete = False
                    continue
                usd += native
                val = native * rate
            else:
                twd += native
                val = native
            if h.market == "CASH":
                cash_twd += val
        if not complete or (rate is None and usd):
            continue
        twd += sum(contracts.value_on(c, day) for c in fixed)
        total = twd + (usd * rate if rate else 0.0)
        months_left = max(
            0, params.target_retire_age * 12 - calculator.age_in_months(params, day)
        )
        db.add(
            PortfolioSnapshot(
                date=d,
                total_value_twd=total,
                total_value_usd=total / rate if rate else 0.0,
                cash_twd=cash_twd,
                fx_rate=rate,
                fx_ma200=fx.mean_last(d, 200),
                coast_target_twd=calculator.coast_target(params, months_left),
            )
        )
    db.flush()


def rebuild_all(db: Session, today: date | None = None) -> None:
    cfg = get_config(db)
    timelines: dict[str, Timeline] = {}
    stock_syms = [h.symbol for h in db.scalars(select(Holding).where(Holding.market != "CASH"))]
    for sym in stock_syms:
        ensure_split_logs(db, sym)
        timelines[sym] = recompute_symbol(db, sym)
    rebuild_dividends(db, cfg, timelines)
    for sym in CASH_SYMBOLS:
        timelines[sym] = recompute_symbol(db, sym)
    rebuild_quotes(db, load_prices(db))
    rebuild_snapshots(db, cfg, timelines, load_prices(db, raw=True), today)


# ------------------------------------------------------------------ user entries

def add_log(
    db: Session,
    symbol: str,
    day: str,
    kind: str,
    delta: float | None = None,
    set_total: float | None = None,
    note: str | None = None,
    price: float | None = None,
) -> ShareLog:
    if kind not in USER_KINDS:
        raise LedgerError(f"不支援的類型：{kind}")
    holding = db.get(Holding, symbol)
    if holding is None:
        raise LedgerError(f"找不到持倉：{symbol}")
    date.fromisoformat(day)  # validates format
    if (delta is None) == (set_total is None):
        raise LedgerError("delta 與 set_total 必須二選一")
    if set_total is not None:
        current = Timeline(_logs(db, symbol)).at(day)
        delta = set_total - current
    assert delta is not None
    if kind in ("sell", "withdraw"):
        delta = -abs(delta)
    elif kind in ("buy", "deposit"):
        delta = abs(delta)
    if abs(delta) < EPS:
        raise LedgerError("股數沒有變動")
    if price is not None and kind == "buy" and price > 0:
        old = holding.shares or 0.0
        old_cost = holding.avg_cost or 0.0
        holding.avg_cost = (old * old_cost + delta * price) / (old + delta)
    log = ShareLog(date=day, symbol=symbol, kind=kind, delta_shares=delta, note=note)
    db.add(log)
    db.flush()
    return log


def position_rows(db: Session, cfg: FireConfig) -> dict:
    """Current positions valued in TWD with the FX mode from config."""
    quotes = {q.symbol: q for q in db.scalars(select(MarketQuote))}
    fxq = quotes.get(FX_SYMBOL)
    live = fxq.close if fxq else None
    ma200 = fxq.ma200 if fxq else None
    if cfg.fx_mode == "custom" and cfg.custom_fx_rate:
        used = cfg.custom_fx_rate
    elif cfg.fx_mode == "ma200" and ma200:
        used = ma200
    else:
        used = live
    rows = []
    for h in db.scalars(select(Holding).order_by(Holding.market.desc(), Holding.symbol)):
        q = quotes.get(h.symbol)
        if h.market == "CASH":
            price = 1.0
        else:
            price = q.close if q else None
        native = h.shares * price if price is not None else None
        rate = used if h.currency == "USD" else 1.0
        value_twd = native * rate if native is not None and rate is not None else None
        live_value_twd = (
            native * (live if h.currency == "USD" else 1.0)
            if native is not None and (live or h.currency == "TWD")
            else None
        )
        cost = h.avg_cost * h.shares if h.avg_cost and h.market != "CASH" else None
        rows.append(
            {
                "symbol": h.symbol,
                "name": h.name,
                "market": h.market,
                "asset_type": h.asset_type,
                "currency": h.currency,
                "shares": h.shares,
                "avg_cost": h.avg_cost,
                "stress_beta": h.stress_beta,
                "target_shares": h.target_shares,
                "archived": h.archived,
                "price": price,
                "price_date": q.date if q else None,
                "prev_close": q.prev_close if q else None,
                "ma20": q.ma20 if q else None,
                "ma60": q.ma60 if q else None,
                "ma200": q.ma200 if q else None,
                "high_52w": q.high_52w if q else None,
                "value_native": native,
                "value_twd": value_twd,
                "live_value_twd": live_value_twd,
                "cost_native": cost,
                "pnl_native": native - cost if native is not None and cost else None,
            }
        )
    today = today_tw()
    for c in db.scalars(select(FixedContract).order_by(FixedContract.id)):
        ci = contracts.info(c, today)
        rows.append(
            {
                "symbol": f"CONTRACT-{c.id}",
                "name": c.name,
                "market": "CONTRACT",
                "asset_type": "contract",
                "currency": "TWD",
                "shares": ci["deposited"],
                "avg_cost": None,
                "stress_beta": 0.0,
                "target_shares": None,
                "archived": c.closed,
                "price": None,
                "price_date": None,
                "prev_close": None,
                "ma20": None,
                "ma60": None,
                "ma200": None,
                "high_52w": None,
                "value_native": ci["value"] if not c.closed else 0.0,
                "value_twd": ci["value"] if not c.closed else 0.0,
                "live_value_twd": ci["value"] if not c.closed else 0.0,
                "cost_native": None,
                "pnl_native": None,
                "contract": ci,
            }
        )
    total = sum(r["value_twd"] or 0 for r in rows)
    for r in rows:
        r["weight"] = (r["value_twd"] or 0) / total if total > 0 else 0
    return {
        "fx": {"mode": cfg.fx_mode, "live": live, "ma200": ma200, "custom": cfg.custom_fx_rate, "used": used},
        "rows": rows,
        "total_twd": total,
    }
