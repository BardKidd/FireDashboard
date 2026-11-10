from datetime import date

import pytest
from sqlalchemy import select

from app import game, ledger
from app.models import Achievement, CorporateAction, Holding, MarketQuote, PriceHistory


def add_holding(db, symbol, market, currency):
    db.add(Holding(symbol=symbol, name=symbol, market=market, currency=currency, shares=0, stress_beta=1))
    db.flush()


def keys(db):
    return set(db.scalars(select(Achievement.key)))


def test_levels():
    assert game.level_for(0) == 1
    assert game.level_for(99) == 1
    assert game.level_for(100) == 2
    assert game.level_for(300) == 3
    assert game.title_for(4) == "小小收藏家"


def test_week_streak_is_forgiving():
    today = date(2026, 11, 11)  # Wednesday
    # Checked in last week and the week before, not yet this week: still alive.
    assert game.week_streak(["2026-10-27", "2026-11-04"], today) == 2
    assert game.week_streak(["2026-10-27", "2026-11-04", "2026-11-10"], today) == 3
    # Missed a whole week: streak restarts.
    assert game.week_streak(["2026-10-20"], today) == 0
    assert game.week_streak([], today) == 0


def test_tw_milestones_use_lots_and_survive_split(db):
    add_holding(db, "0050.TW", "TW", "TWD")
    db.add(CorporateAction(symbol="0050.TW", date="2025-06-18", kind="split", value=4))
    ledger.add_log(db, "0050.TW", "2025-06-01", "buy", delta=500)  # = 2000 post-split
    ledger.add_log(db, "0050.TW", "2025-07-01", "buy", delta=1000)  # 3000
    ledger.rebuild_all(db, today=date(2025, 7, 2))
    game.sync(db)
    k = keys(db)
    assert {"first:0050.TW", "ms:0050.TW:100", "ms:0050.TW:500", "ms:0050.TW:1000", "ms:0050.TW:3000"} <= k
    assert "ms:0050.TW:5000" not in k
    a = db.get(Achievement, "ms:0050.TW:2000")
    assert a.title == "0050 2 張"
    assert a.earned_on == "2025-06-01"  # pre-split shares restated, no jump on split day

    curve, _ = game._adjusted_logs(db, "0050.TW")
    assert [p.shares for p in curve] == [2000, 3000]


def test_achievements_are_never_revoked(db):
    add_holding(db, "VOO", "US", "USD")
    log = ledger.add_log(db, "VOO", "2025-06-01", "buy", delta=5)
    ledger.rebuild_all(db, today=date(2025, 7, 1))
    game.sync(db)
    assert "ms:VOO:5" in keys(db)
    db.delete(log)
    ledger.rebuild_all(db, today=date(2025, 7, 1))
    game.sync(db)
    assert "ms:VOO:5" in keys(db)


def test_checkin_rewards_and_redeem(db):
    game.checkin(db, today=date(2026, 11, 10))
    with pytest.raises(game.GameError):
        game.checkin(db, today=date(2026, 11, 10))
    r = game.checkin(db, today=date(2026, 11, 11), note="今天很平靜")
    assert r["points"] == 10 and r["total_days"] == 2 and r["since"] == "2026-11-10"
    earned, spent, bal = game.balance(db)
    assert earned == 10 + 10 + 20  # two check-ins + first check-in badge

    from app.models import Reward

    rw = Reward(name="一杯好咖啡", cost=30, repeatable=False)
    db.add(rw)
    db.flush()
    game.redeem(db, rw.id, today=date(2026, 11, 11))
    assert game.balance(db)[2] == 10
    with pytest.raises(game.GameError):
        game.redeem(db, rw.id)  # not repeatable
    # Spending never lowers the level.
    assert game.state(db, today=date(2026, 11, 11))["level"]["xp"] == 40


def test_theme_locked_until_level(db):
    with pytest.raises(game.GameError):
        game.set_settings(db, "gold", None)
    game.set_settings(db, "teal", "fire")
    assert game.collect_view(db, date(2026, 11, 10))["basket_goal"] == "fire"


def test_collect_view_targets_and_radar(db):
    add_holding(db, "VOO", "US", "USD")
    ledger.add_log(db, "VOO", "2026-01-05", "buy", delta=10)
    for d in ("2026-11-06", "2026-11-09"):
        db.add(PriceHistory(symbol="VOO", date=d, close=500.0))
        db.add(PriceHistory(symbol="USDTWD=X", date=d, close=30.0))
    ledger.rebuild_all(db, today=date(2026, 11, 10))
    q = db.get(MarketQuote, "VOO")
    q.ma60, q.ma200, q.high_52w = 550.0, 400.0, 625.0
    db.flush()
    v = game.collect_view(db, date(2026, 11, 10))
    row = v["holdings"][0]
    assert row["level"] == 3 and row["next_milestone"] == 20 and row["progress_to_next"] == pytest.approx(0)
    assert row["radar"]["extra_vs_ma60"] == pytest.approx(0.1)
    assert row["radar"]["discount_vs_high"] == pytest.approx(0.2)
    # All value is VOO, so target = goal / (ma200 * fx).
    assert row["target_shares"] == pytest.approx(v["goal_amount"] / (400 * 30))
