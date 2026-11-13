"""yfinance price, dividend, split and FX fetching with backfill (SPEC.md 4)."""
from __future__ import annotations

import logging
import re
import time
from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from .database import SessionLocal, write_lock
from .ledger import rebuild_all, today_tw
from .models import (
    FX_SYMBOL,
    CorporateAction,
    FetchStatus,
    Holding,
    PriceHistory,
)

log = logging.getLogger("fire.fetcher")

INITIAL_YEARS = 2
RETRIES = (2, 4, 8)
LEVERAGED = {"SSO", "QLD", "UPRO", "TQQQ", "SPXL", "SOXL", "TECL", "UWM", "DDM"}
TRIPLE = {"UPRO", "TQQQ", "SPXL", "SOXL", "TECL"}


class FetchError(RuntimeError):
    pass


def _is_rate_limit(exc: Exception) -> bool:
    return "RateLimit" in type(exc).__name__ or "Too Many Requests" in str(exc)


# ------------------------------------------------------------------ symbols

def guess_meta(symbol: str) -> dict:
    """Market, currency and default asset type for a normalised symbol."""
    if symbol.endswith(".TW") or symbol.endswith(".TWO"):
        code = symbol.split(".")[0]
        bond = code.endswith("B")
        lev = code.endswith("L")
        return {
            "market": "TW",
            "currency": "TWD",
            "asset_type": "bond" if bond else ("leveraged" if lev else "equity"),
            "stress_beta": 0.0 if bond else (2.0 if lev else 1.0),
        }
    lev = symbol in LEVERAGED
    return {
        "market": "US",
        "currency": "USD",
        "asset_type": "leveraged" if lev else "equity",
        "stress_beta": (3.0 if symbol in TRIPLE else 2.0) if lev else 1.0,
    }


def _download(tickers: list[str], start: date, end: date | None = None) -> tuple[pd.DataFrame, dict]:
    """Batched download. Returns (frame, {ticker: error message})."""
    import yfinance as yf
    import yfinance.shared as yf_shared

    last_exc: Exception | None = None
    for wait in (0, *RETRIES):
        if wait:
            time.sleep(wait)
        try:
            df = yf.download(
                tickers,
                start=start.isoformat(),
                end=(end or today_tw() + timedelta(days=1)).isoformat(),
                auto_adjust=False,
                actions=True,
                group_by="ticker",
                progress=False,
                threads=False,
            )
            errors = {k: str(v) for k, v in dict(getattr(yf_shared, "_ERRORS", {}) or {}).items()}
            return df, errors
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if _is_rate_limit(exc):
                break  # wait for the next scheduled run instead of hammering
    raise FetchError(str(last_exc))


def _frame_for(df: pd.DataFrame, ticker: str) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        if ticker not in df.columns.get_level_values(0):
            return None
        sub = df[ticker]
    else:
        sub = df
    sub = sub.dropna(subset=["Close"])
    return sub if not sub.empty else None


def probe(symbol: str) -> bool:
    try:
        df, _ = _download([symbol], today_tw() - timedelta(days=14))
    except FetchError:
        return False
    return _frame_for(df, symbol) is not None


def normalize_symbol(raw: str) -> str:
    """'0050' -> '0050.TW' or '.TWO'; 'voo' -> 'VOO'. Raises if unknown."""
    s = raw.strip().upper()
    if not s:
        raise FetchError("代號不可為空")
    if s.endswith(".TW") or s.endswith(".TWO") or s == FX_SYMBOL:
        candidates = [s]
    elif re.fullmatch(r"\d{4,6}[A-Z]?", s):
        candidates = [f"{s}.TW", f"{s}.TWO"]
    else:
        candidates = [s]
    for c in candidates:
        if probe(c):
            return c
    raise FetchError(f"Yahoo Finance 找不到 {raw}（試過 {', '.join(candidates)}）")


def lookup_name(symbol: str) -> str:
    try:
        import yfinance as yf

        info = yf.Ticker(symbol).info or {}
        return info.get("shortName") or info.get("longName") or symbol
    except Exception:  # noqa: BLE001
        return symbol


# ------------------------------------------------------------------ storing

# Splits Yahoo has already applied to its prices but does not list as an event.
KNOWN_SPLITS: dict[str, list[tuple[str, float]]] = {
    "0050.TW": [("2025-06-18", 4.0)],
}


def _store(db: Session, symbol: str, frame: pd.DataFrame, kind: str) -> int:
    """Store Yahoo closes as returned (split-adjusted) plus corporate actions.

    Every run re-downloads the whole window, so stored rows always share one
    adjustment basis; ledger.load_prices converts them back to raw prices.
    """
    frame = frame.sort_index()
    now = datetime.now()
    written = 0
    for idx, row in frame.iterrows():
        d = idx.date().isoformat()
        close = float(row["Close"])
        stmt = sqlite_insert(PriceHistory).values(symbol=symbol, date=d, close=close, fetched_at=now)
        db.execute(
            stmt.on_conflict_do_update(
                index_elements=["symbol", "date"], set_={"close": close, "fetched_at": now}
            )
        )
        written += 1
    if kind != "fx":
        if "Stock Splits" in frame:
            sp = frame["Stock Splits"]
            for idx, r in sp[sp.fillna(0) > 0].items():
                if float(r) != 1.0:
                    upsert_action(db, symbol, idx.date().isoformat(), "split", float(r))
        for d, r in KNOWN_SPLITS.get(symbol, []):
            upsert_action(db, symbol, d, "split", r)
        if "Dividends" in frame:
            dv = frame["Dividends"]
            for idx, v in dv[dv.fillna(0) > 0].items():
                upsert_action(db, symbol, idx.date().isoformat(), "dividend", float(v))
    return written


def upsert_action(db: Session, symbol: str, d: str, kind: str, value: float) -> None:
    stmt = sqlite_insert(CorporateAction).values(symbol=symbol, date=d, kind=kind, value=value)
    db.execute(
        stmt.on_conflict_do_update(index_elements=["symbol", "date", "kind"], set_={"value": value})
    )


def _status(db: Session, symbol: str) -> FetchStatus:
    st = db.get(FetchStatus, symbol)
    if st is None:
        st = FetchStatus(symbol=symbol)
        db.add(st)
    return st


# ------------------------------------------------------------------ main entry

def _start_for(need_from: str | None) -> date:
    """Always fetch the full window: one batched request keeps every stored
    row on the same split-adjustment basis."""
    start = today_tw() - timedelta(days=365 * INITIAL_YEARS + 10)
    if need_from:
        start = min(start, date.fromisoformat(need_from) - timedelta(days=10))
    return start


def tracked_symbols(db: Session) -> list[str]:
    """Symbols the scheduled refresh keeps up to date: every non-cash holding
    still held (or not archived), plus the FX rate. Sold-and-archived holdings
    are left out, so their frozen fetch status must not count as stale."""
    holdings = db.scalars(select(Holding).where(Holding.market != "CASH"))
    syms = [h.symbol for h in holdings if not h.archived or h.shares > 0]
    return list(dict.fromkeys([*syms, FX_SYMBOL]))


def refresh(symbols: list[str] | None = None) -> dict:
    """Fetch new data for all (or given) symbols, then rebuild derived tables."""
    results: dict[str, str] = {}
    with write_lock, SessionLocal() as db:
        from .models import ShareLog

        targets = list(dict.fromkeys([*symbols, FX_SYMBOL])) if symbols else tracked_symbols(db)
        first_log = {
            s: d
            for s, d in db.execute(
                select(ShareLog.symbol, func.min(ShareLog.date)).group_by(ShareLog.symbol)
            ).all()
        }
        overall_first = min(first_log.values()) if first_log else None

        # Group by start date so most runs are one batched request.
        groups: dict[date, list[str]] = {}
        for sym in targets:
            need = overall_first if sym == FX_SYMBOL else first_log.get(sym)
            groups.setdefault(_start_for(need), []).append(sym)

        rate_limited = False
        for start, syms in groups.items():
            if rate_limited:
                for s in syms:
                    results[s] = "skipped (rate limited)"
                continue
            try:
                df, errors = _download(syms, start)
            except FetchError as exc:
                rate_limited = "RateLimit" in str(exc) or "Too Many" in str(exc)
                for s in syms:
                    st = _status(db, s)
                    st.last_attempt_at = datetime.now()
                    st.last_error = str(exc)[:500]
                    results[s] = f"error: {exc}"
                continue
            for s in syms:
                st = _status(db, s)
                st.last_attempt_at = datetime.now()
                frame = _frame_for(df, s)
                if frame is None:
                    st.last_error = (errors.get(s) or "no data returned")[:500]
                    results[s] = f"error: {st.last_error}"
                    if "Rate" in st.last_error or "429" in st.last_error:
                        rate_limited = True
                    continue
                n = _store(db, s, frame, "fx" if s == FX_SYMBOL else "stock")
                st.last_success_date = frame.index.max().date().isoformat()
                st.last_error = None
                results[s] = f"ok ({n} rows)"
        db.flush()
        rebuild_all(db)
        db.commit()
    log.info("refresh done: %s", results)
    return results
