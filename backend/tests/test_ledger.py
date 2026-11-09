from datetime import date

import pytest
from sqlalchemy import select

from app import ledger
from app.models import (
    CASH_TWD, CASH_USD, FX_SYMBOL, CorporateAction, Dividend, Holding, PortfolioSnapshot,
    PriceHistory, get_config,
)


def add_holding(db, symbol, market, currency):
    db.add(Holding(symbol=symbol, name=symbol, market=market, currency=currency, shares=0, stress_beta=1))
    db.flush()


def price(db, symbol, d, close):
    db.add(PriceHistory(symbol=symbol, date=d, close=close))


def test_split_applies_to_backdated_buys(db):
    add_holding(db, "0050.TW", "TW", "TWD")
    db.add(CorporateAction(symbol="0050.TW", date="2025-06-18", kind="split", value=4))
    ledger.add_log(db, "0050.TW", "2025-07-01", "buy", delta=100)
    ledger.rebuild_all(db, today=date(2025, 7, 2))
    assert db.get(Holding, "0050.TW").shares == 100
    # Backdate 10 pre-split shares: they become 40.
    ledger.add_log(db, "0050.TW", "2025-06-01", "buy", delta=10)
    ledger.rebuild_all(db, today=date(2025, 7, 2))
    assert db.get(Holding, "0050.TW").shares == pytest.approx(140)


def test_snapshot_value_is_continuous_across_split(db):
    add_holding(db, "0050.TW", "TW", "TWD")
    db.add(CorporateAction(symbol="0050.TW", date="2025-06-18", kind="split", value=4))
    # Yahoo-style split-adjusted closes: flat price of 47 adjusted == 188 raw before the split.
    for d in ["2025-06-16", "2025-06-17", "2025-06-18", "2025-06-19"]:
        price(db, "0050.TW", d, 47.0)
    price(db, FX_SYMBOL, "2025-06-16", 30.0)
    ledger.add_log(db, "0050.TW", "2025-06-16", "buy", delta=1000)
    ledger.rebuild_all(db, today=date(2025, 6, 19))
    snaps = {s.date: s.total_value_twd for s in db.scalars(select(PortfolioSnapshot))}
    assert snaps["2025-06-17"] == pytest.approx(1000 * 188)
    assert snaps["2025-06-18"] == pytest.approx(4000 * 47)


def test_us_dividend_withholding(db):
    add_holding(db, "VOO", "US", "USD")
    db.add(CorporateAction(symbol="VOO", date="2025-06-30", kind="dividend", value=1.745))
    ledger.add_log(db, "VOO", "2025-06-01", "buy", delta=10)
    ledger.add_log(db, "VOO", "2025-06-30", "buy", delta=5)  # bought on ex-date: not eligible
    ledger.rebuild_all(db, today=date(2025, 7, 1))
    d = db.scalars(select(Dividend)).one()
    assert d.shares_held == 10
    assert d.net == pytest.approx(17.45 * 0.7)
    assert db.get(Holding, CASH_USD).shares == pytest.approx(17.45 * 0.7)


def test_tw_dividend_nhi_threshold(db):
    add_holding(db, "0056.TW", "TW", "TWD")
    db.add(CorporateAction(symbol="0056.TW", date="2025-07-16", kind="dividend", value=1.0))
    db.add(CorporateAction(symbol="0056.TW", date="2025-10-16", kind="dividend", value=1.0))
    ledger.add_log(db, "0056.TW", "2025-07-01", "buy", delta=19_999)
    ledger.add_log(db, "0056.TW", "2025-08-01", "buy", delta=1_001)
    ledger.rebuild_all(db, today=date(2025, 11, 1))
    divs = {d.ex_date: d for d in db.scalars(select(Dividend))}
    assert divs["2025-07-16"].nhi_premium == 0
    assert divs["2025-10-16"].nhi_premium == pytest.approx(21_000 * 0.0211)
    assert db.get(Holding, CASH_TWD).shares == pytest.approx(19_999 + 21_000 * (1 - 0.0211))


def test_dividend_per_share_unadjusted_for_later_split(db):
    add_holding(db, "0050.TW", "TW", "TWD")
    db.add(CorporateAction(symbol="0050.TW", date="2025-06-18", kind="split", value=4))
    db.add(CorporateAction(symbol="0050.TW", date="2025-01-17", kind="dividend", value=0.675))
    ledger.add_log(db, "0050.TW", "2025-01-01", "buy", delta=1000)
    ledger.rebuild_all(db, today=date(2025, 7, 1))
    d = db.scalars(select(Dividend)).one()
    assert d.per_share == pytest.approx(2.7)
    assert d.gross == pytest.approx(2700)


def test_negative_shares_rejected(db):
    add_holding(db, "VOO", "US", "USD")
    ledger.add_log(db, "VOO", "2025-06-01", "buy", delta=10)
    ledger.add_log(db, "VOO", "2025-05-01", "sell", delta=5)
    with pytest.raises(ledger.LedgerError):
        ledger.rebuild_all(db, today=date(2025, 7, 1))


def test_set_total(db):
    add_holding(db, "VOO", "US", "USD")
    ledger.add_log(db, "VOO", "2025-06-01", "buy", delta=10)
    ledger.rebuild_all(db, today=date(2025, 7, 1))
    log = ledger.add_log(db, "VOO", "2025-06-10", "adjust", set_total=12.5)
    assert log.delta_shares == pytest.approx(2.5)


def test_us_price_uses_previous_close(db):
    add_holding(db, "VOO", "US", "USD")
    price(db, "VOO", "2025-06-02", 500)
    price(db, "VOO", "2025-06-03", 510)
    price(db, FX_SYMBOL, "2025-06-02", 30)
    price(db, FX_SYMBOL, "2025-06-03", 30)
    ledger.add_log(db, "VOO", "2025-06-02", "buy", delta=1)
    ledger.rebuild_all(db, today=date(2025, 6, 3))
    snaps = {s.date: s.total_value_twd for s in db.scalars(select(PortfolioSnapshot))}
    assert snaps["2025-06-03"] == pytest.approx(500 * 30)


def test_position_rows_fx_modes(db):
    add_holding(db, "VOO", "US", "USD")
    for i in range(200):
        price(db, FX_SYMBOL, f"2025-{1 + i // 28:02d}-{1 + i % 28:02d}", 30 + (i == 199) * 2)
    price(db, "VOO", "2025-06-02", 500)
    ledger.add_log(db, "VOO", "2025-06-02", "buy", delta=2)
    ledger.rebuild_all(db, today=date(2025, 8, 1))
    cfg = get_config(db)
    cfg.fx_mode = "live"
    assert ledger.position_rows(db, cfg)["total_twd"] == pytest.approx(1000 * 32)
    cfg.fx_mode = "ma200"
    assert ledger.position_rows(db, cfg)["total_twd"] == pytest.approx(1000 * (30 + 2 / 200))
    cfg.fx_mode, cfg.custom_fx_rate = "custom", 29
    assert ledger.position_rows(db, cfg)["total_twd"] == pytest.approx(29_000)
