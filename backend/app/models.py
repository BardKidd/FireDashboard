"""Table definitions. See SPEC.md section 3.

Source-of-truth tables: share_logs (user entries + split rows), price_history,
corporate_actions. Everything else (holdings.shares, dividends, cash dividend
rows, market_quotes, portfolio_snapshots) is derived and rebuilt by ledger.py.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from .database import Base

FX_SYMBOL = "USDTWD=X"
CASH_TWD = "CASH-TWD"
CASH_USD = "CASH-USD"
CASH_SYMBOLS = {CASH_TWD: "TWD", CASH_USD: "USD"}


def _now() -> datetime:
    return datetime.now()


class FireConfig(Base):
    __tablename__ = "fire_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    birth_year: Mapped[int] = mapped_column(Integer, default=1995)
    birth_month: Mapped[int] = mapped_column(Integer, default=1)
    target_retire_age: Mapped[int] = mapped_column(Integer, default=55)
    annual_expense_twd: Mapped[float] = mapped_column(Float, default=600_000)
    swr: Mapped[float] = mapped_column(Float, default=0.038)
    expected_nominal_return: Mapped[float] = mapped_column(Float, default=0.085)
    inflation_rate: Mapped[float] = mapped_column(Float, default=0.025)
    monthly_contribution_twd: Mapped[float] = mapped_column(Float, default=30_000)
    contribution_indexed: Mapped[bool] = mapped_column(Boolean, default=True)
    fx_mode: Mapped[str] = mapped_column(String(10), default="ma200")  # live|ma200|custom
    custom_fx_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    stress_drop: Mapped[float] = mapped_column(Float, default=0.20)
    us_dividend_tax: Mapped[float] = mapped_column(Float, default=0.30)
    tw_nhi_rate: Mapped[float] = mapped_column(Float, default=0.0211)
    tw_nhi_threshold: Mapped[float] = mapped_column(Float, default=20_000)


class Holding(Base):
    __tablename__ = "holdings"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    market: Mapped[str] = mapped_column(String(4))  # US|TW|CASH
    asset_type: Mapped[str] = mapped_column(String(10), default="equity")  # equity|leveraged|bond|cash
    currency: Mapped[str] = mapped_column(String(3))  # USD|TWD
    shares: Mapped[float] = mapped_column(Float, default=0.0)
    avg_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    stress_beta: Mapped[float] = mapped_column(Float, default=1.0)
    target_shares: Mapped[float | None] = mapped_column(Float, nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class ShareLog(Base):
    __tablename__ = "share_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    # buy|sell|adjust|deposit|withdraw (user) ; split|dividend (system)
    kind: Mapped[str] = mapped_column(String(10))
    delta_shares: Mapped[float] = mapped_column(Float, default=0.0)
    split_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_shares_after: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # For kind=dividend rows on a cash symbol: the stock that paid it.
    source_symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class CorporateAction(Base):
    """Raw dividend / split events from Yahoo, un-adjusted for later splits."""

    __tablename__ = "corporate_actions"
    __table_args__ = (UniqueConstraint("symbol", "date", "kind"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    date: Mapped[str] = mapped_column(String(10))
    kind: Mapped[str] = mapped_column(String(10))  # dividend|split
    value: Mapped[float] = mapped_column(Float)  # per-share cash, or split ratio


class Dividend(Base):
    __tablename__ = "dividends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    ex_date: Mapped[str] = mapped_column(String(10))
    per_share: Mapped[float] = mapped_column(Float)
    shares_held: Mapped[float] = mapped_column(Float)
    gross: Mapped[float] = mapped_column(Float)
    tax_withheld: Mapped[float] = mapped_column(Float, default=0.0)
    nhi_premium: Mapped[float] = mapped_column(Float, default=0.0)
    net: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))


class PriceHistory(Base):
    __tablename__ = "price_history"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    date: Mapped[str] = mapped_column(String(10), primary_key=True)
    close: Mapped[float] = mapped_column(Float)  # raw close, not split/dividend adjusted
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class MarketQuote(Base):
    __tablename__ = "market_quotes"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    date: Mapped[str] = mapped_column(String(10))
    close: Mapped[float] = mapped_column(Float)
    prev_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma20: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma60: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma200: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_52w: Mapped[float | None] = mapped_column(Float, nullable=True)


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    date: Mapped[str] = mapped_column(String(10), primary_key=True)
    total_value_twd: Mapped[float] = mapped_column(Float)
    total_value_usd: Mapped[float] = mapped_column(Float)
    cash_twd: Mapped[float] = mapped_column(Float)
    fx_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    fx_ma200: Mapped[float | None] = mapped_column(Float, nullable=True)
    coast_target_twd: Mapped[float | None] = mapped_column(Float, nullable=True)


class FixedContract(Base):
    """A fixed-payout savings agreement, e.g. deposit 5,000 TWD a month for
    60 months and receive 350,000 TWD at the end."""

    __tablename__ = "fixed_contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    start_month: Mapped[str] = mapped_column(String(7))  # YYYY-MM of the first deposit
    monthly_deposit: Mapped[float] = mapped_column(Float)
    term_months: Mapped[int] = mapped_column(Integer)
    payout: Mapped[float] = mapped_column(Float)
    valuation: Mapped[str] = mapped_column(String(10), default="accrued")  # accrued|deposited
    closed: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Checkin(Base):
    """Phase 2: one row per Taiwan date the user checked in."""

    __tablename__ = "checkins"

    date: Mapped[str] = mapped_column(String(10), primary_key=True)
    points: Mapped[int] = mapped_column(Integer, default=10)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Achievement(Base):
    """Phase 2: unlocked badges and point events. Rows are only ever added,
    never revoked, so a later correction can't take a reward away."""

    __tablename__ = "achievements"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    category: Mapped[str] = mapped_column(String(12))  # milestone|coast|checkin|streak|dividend|first
    title: Mapped[str] = mapped_column(String(100))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    earned_on: Mapped[str] = mapped_column(String(10))
    points: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Reward(Base):
    """Phase 2: a real-life reward the user sets a star price for."""

    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    cost: Mapped[int] = mapped_column(Integer)
    repeatable: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Redemption(Base):
    __tablename__ = "redemptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reward_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(100))
    cost: Mapped[int] = mapped_column(Integer)
    date: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class GameSettings(Base):
    __tablename__ = "game_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    theme: Mapped[str] = mapped_column(String(20), default="ember")
    basket_goal: Mapped[str] = mapped_column(String(10), default="coast")  # coast|fire


class FetchStatus(Base):
    __tablename__ = "fetch_status"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    last_success_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


def ensure_defaults(db: Session) -> None:
    if db.get(FireConfig, 1) is None:
        db.add(FireConfig(id=1))
    if db.get(GameSettings, 1) is None:
        db.add(GameSettings(id=1))
    for sym, cur in CASH_SYMBOLS.items():
        if db.get(Holding, sym) is None:
            db.add(
                Holding(
                    symbol=sym,
                    name="台幣現金" if cur == "TWD" else "美金現金",
                    market="CASH",
                    asset_type="cash",
                    currency=cur,
                    shares=0.0,
                    stress_beta=0.0,
                )
            )


def get_config(db: Session) -> FireConfig:
    cfg = db.get(FireConfig, 1)
    if cfg is None:
        ensure_defaults(db)
        db.flush()
        cfg = db.get(FireConfig, 1)
    return cfg


def active_holdings(db: Session) -> list[Holding]:
    return list(db.scalars(select(Holding).order_by(Holding.market, Holding.symbol)))
