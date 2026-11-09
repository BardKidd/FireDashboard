"""FastAPI entry point, REST API and scheduler."""
from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from datetime import date
from typing import Literal

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import calculator, database, fetcher, ledger
from .database import get_db, write_lock
from .models import (
    CASH_SYMBOLS,
    FX_SYMBOL,
    CorporateAction,
    Dividend,
    FetchStatus,
    Holding,
    PortfolioSnapshot,
    PriceHistory,
    ShareLog,
    get_config,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("fire")

_refresh_lock = threading.Lock()
_refresh_state = {"running": False, "last_result": None}


def run_refresh(symbols: list[str] | None = None) -> None:
    if not _refresh_lock.acquire(blocking=False):
        return
    _refresh_state["running"] = True
    try:
        _refresh_state["last_result"] = fetcher.refresh(symbols)
    except Exception as exc:  # noqa: BLE001
        log.exception("refresh failed")
        _refresh_state["last_result"] = {"error": str(exc)}
    finally:
        _refresh_state["running"] = False
        _refresh_lock.release()


def refresh_in_background(symbols: list[str] | None = None) -> None:
    threading.Thread(target=run_refresh, args=(symbols,), daemon=True).start()


scheduler = BackgroundScheduler(timezone="Asia/Taipei")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    database.init_db()
    import os

    if os.environ.get("FIRE_DISABLE_SCHEDULER") != "1":
        # 14:30 after TW close; 06:30 after US close (Tue-Sat covers Mon-Fri US sessions).
        scheduler.add_job(run_refresh, "cron", day_of_week="mon-fri", hour=14, minute=30, id="tw")
        scheduler.add_job(run_refresh, "cron", day_of_week="tue-sat", hour=6, minute=30, id="us")
        scheduler.start()
        refresh_in_background()  # startup backfill
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="FireDashboard", lifespan=lifespan)


# ------------------------------------------------------------------ helpers

def _rebuild(db: Session) -> None:
    try:
        ledger.rebuild_all(db)
    except ledger.LedgerError as exc:
        db.rollback()
        raise HTTPException(400, str(exc)) from exc


def _summary(db: Session) -> dict:
    cfg = get_config(db)
    pos = ledger.position_rows(db, cfg)
    params = calculator.FireParams.from_config(cfg)
    pairs = [(r["value_twd"] or 0, r["stress_beta"]) for r in pos["rows"]]
    beta = calculator.portfolio_beta(pairs)
    today = ledger.today_tw()
    s = calculator.summary(params, pos["total_twd"], beta, today)
    live_total = sum(r["live_value_twd"] or 0 for r in pos["rows"])
    s["total_assets_live_fx"] = live_total
    s["fx"] = pos["fx"]
    last = db.scalar(select(PortfolioSnapshot).order_by(PortfolioSnapshot.date.desc()))
    prev = None
    if last:
        prev = db.scalar(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.date < last.date)
            .order_by(PortfolioSnapshot.date.desc())
        )
    s["day_change_twd"] = (last.total_value_twd - prev.total_value_twd) if last and prev else None
    s["missing_prices"] = [
        r["symbol"] for r in pos["rows"] if r["market"] != "CASH" and r["shares"] > 0 and r["price"] is None
    ]
    return s


# ------------------------------------------------------------------ config

class ConfigIn(BaseModel):
    birth_year: int = Field(ge=1900, le=2100)
    birth_month: int = Field(ge=1, le=12)
    target_retire_age: int = Field(ge=18, le=100)
    annual_expense_twd: float = Field(gt=0)
    swr: float = Field(gt=0, lt=1)
    expected_nominal_return: float = Field(gt=-0.5, lt=1)
    inflation_rate: float = Field(gt=-0.5, lt=1)
    monthly_contribution_twd: float = Field(ge=0)
    contribution_indexed: bool
    fx_mode: Literal["live", "ma200", "custom"]
    custom_fx_rate: float | None = Field(default=None, gt=0)
    stress_drop: float = Field(gt=0, le=1)
    us_dividend_tax: float = Field(ge=0, lt=1)
    tw_nhi_rate: float = Field(ge=0, lt=1)
    tw_nhi_threshold: float = Field(ge=0)


@app.get("/api/config")
def read_config(db: Session = Depends(get_db)):
    cfg = get_config(db)
    return {k: getattr(cfg, k) for k in ConfigIn.model_fields}


@app.put("/api/config")
def write_config(body: ConfigIn, db: Session = Depends(get_db)):
    if body.fx_mode == "custom" and not body.custom_fx_rate:
        raise HTTPException(400, "自訂匯率模式需要填入匯率")
    with write_lock:
        cfg = get_config(db)
        for k, v in body.model_dump().items():
            setattr(cfg, k, v)
        _rebuild(db)  # tax settings and coast targets feed derived tables
        db.commit()
    return read_config(db)


# ------------------------------------------------------------------ holdings

class HoldingIn(BaseModel):
    symbol: str
    name: str | None = None
    shares: float = Field(default=0, ge=0)
    date: str | None = None  # date the initial shares were held from
    avg_cost: float | None = Field(default=None, ge=0)
    asset_type: Literal["equity", "leveraged", "bond"] | None = None
    stress_beta: float | None = None
    note: str | None = None


class HoldingPatch(BaseModel):
    name: str | None = None
    avg_cost: float | None = Field(default=None, ge=0)
    asset_type: Literal["equity", "leveraged", "bond", "cash"] | None = None
    stress_beta: float | None = None
    target_shares: float | None = Field(default=None, ge=0)
    archived: bool | None = None


@app.get("/api/holdings")
def list_holdings(db: Session = Depends(get_db)):
    return ledger.position_rows(db, get_config(db))


@app.post("/api/holdings", status_code=201)
def create_holding(body: HoldingIn, db: Session = Depends(get_db)):
    try:
        symbol = fetcher.normalize_symbol(body.symbol)
    except fetcher.FetchError as exc:
        raise HTTPException(400, str(exc)) from exc
    with write_lock:
        existing = db.get(Holding, symbol)
        if existing is not None and not existing.archived:
            raise HTTPException(409, f"{symbol} 已在持倉中")
        meta = fetcher.guess_meta(symbol)
        if body.asset_type:
            meta["asset_type"] = body.asset_type
            meta["stress_beta"] = {"bond": 0.0, "leveraged": 2.0}.get(body.asset_type, 1.0)
        if body.stress_beta is not None:
            meta["stress_beta"] = body.stress_beta
        if existing is None:
            existing = Holding(symbol=symbol, shares=0.0, **meta)
            db.add(existing)
        existing.archived = False
        existing.name = body.name or existing.name or fetcher.lookup_name(symbol)
        if body.avg_cost is not None:
            existing.avg_cost = body.avg_cost
        db.flush()
        if body.shares > 0:
            ledger.add_log(
                db, symbol, body.date or ledger.today_tw().isoformat(), "adjust",
                delta=body.shares, note=body.note or "初始持倉",
            )
        _rebuild(db)
        db.commit()
    refresh_in_background()
    return {"symbol": symbol}


@app.patch("/api/holdings/{symbol}")
def patch_holding(symbol: str, body: HoldingPatch, db: Session = Depends(get_db)):
    with write_lock:
        h = db.get(Holding, symbol)
        if h is None:
            raise HTTPException(404, "找不到持倉")
        for k, v in body.model_dump(exclude_unset=True).items():
            setattr(h, k, v)
        db.commit()
    return {"ok": True}


@app.delete("/api/holdings/{symbol}")
def delete_holding(symbol: str, db: Session = Depends(get_db)):
    """Delete if it never had entries; otherwise archive so history stays intact."""
    if symbol in CASH_SYMBOLS:
        raise HTTPException(400, "現金部位不可刪除")
    with write_lock:
        h = db.get(Holding, symbol)
        if h is None:
            raise HTTPException(404, "找不到持倉")
        has_logs = db.scalar(select(ShareLog.id).where(ShareLog.symbol == symbol).limit(1))
        if has_logs:
            h.archived = True
            db.commit()
            return {"archived": True}
        db.delete(h)
        db.execute(delete(PriceHistory).where(PriceHistory.symbol == symbol))
        db.execute(delete(CorporateAction).where(CorporateAction.symbol == symbol))
        db.execute(delete(FetchStatus).where(FetchStatus.symbol == symbol))
        _rebuild(db)
        db.commit()
    return {"deleted": True}


# ------------------------------------------------------------------ share logs

class LogIn(BaseModel):
    symbol: str
    date: str
    kind: Literal["buy", "sell", "adjust", "deposit", "withdraw"]
    delta: float | None = None
    set_total: float | None = Field(default=None, ge=0)
    price: float | None = Field(default=None, gt=0)
    note: str | None = None


class LogPatch(BaseModel):
    date: str | None = None
    delta: float | None = None
    note: str | None = None


def _log_dict(l: ShareLog) -> dict:
    return {
        "id": l.id, "date": l.date, "symbol": l.symbol, "kind": l.kind,
        "delta_shares": l.delta_shares, "split_ratio": l.split_ratio,
        "total_shares_after": l.total_shares_after, "note": l.note,
        "source_symbol": l.source_symbol, "created_at": l.created_at,
    }


@app.get("/api/logs")
def list_logs(symbol: str | None = None, db: Session = Depends(get_db)):
    q = select(ShareLog).order_by(ShareLog.date.desc(), ShareLog.id.desc())
    if symbol:
        q = q.where(ShareLog.symbol == symbol)
    return [_log_dict(l) for l in db.scalars(q)]


@app.post("/api/logs", status_code=201)
def create_log(body: LogIn, db: Session = Depends(get_db)):
    with write_lock:
        try:
            date.fromisoformat(body.date)
            entry = ledger.add_log(
                db, body.symbol, body.date, body.kind, delta=body.delta,
                set_total=body.set_total, note=body.note, price=body.price,
            )
        except (ledger.LedgerError, ValueError) as exc:
            db.rollback()
            raise HTTPException(400, str(exc)) from exc
        _rebuild(db)
        db.commit()
        need_backfill = db.scalar(
            select(PriceHistory.date).where(PriceHistory.symbol == body.symbol).order_by(PriceHistory.date)
        )
    if body.symbol not in CASH_SYMBOLS and (need_backfill is None or body.date < need_backfill):
        refresh_in_background()
    return _log_dict(entry)


@app.patch("/api/logs/{log_id}")
def patch_log(log_id: int, body: LogPatch, db: Session = Depends(get_db)):
    with write_lock:
        l = db.get(ShareLog, log_id)
        if l is None:
            raise HTTPException(404, "找不到紀錄")
        if l.kind in ("split", "dividend"):
            raise HTTPException(400, "系統自動產生的紀錄不可修改")
        if body.date is not None:
            try:
                date.fromisoformat(body.date)
            except ValueError as exc:
                raise HTTPException(400, "日期格式錯誤") from exc
            l.date = body.date
        if body.delta is not None:
            if abs(body.delta) < ledger.EPS:
                raise HTTPException(400, "股數沒有變動")
            l.delta_shares = body.delta
        if body.note is not None:
            l.note = body.note
        _rebuild(db)
        db.commit()
    return _log_dict(l)


@app.delete("/api/logs/{log_id}")
def delete_log(log_id: int, db: Session = Depends(get_db)):
    with write_lock:
        l = db.get(ShareLog, log_id)
        if l is None:
            raise HTTPException(404, "找不到紀錄")
        if l.kind in ("split", "dividend"):
            raise HTTPException(400, "系統自動產生的紀錄不可刪除")
        db.delete(l)
        _rebuild(db)
        db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ splits (manual)

class SplitIn(BaseModel):
    symbol: str
    date: str
    ratio: float = Field(gt=0)


@app.get("/api/splits")
def list_splits(db: Session = Depends(get_db)):
    q = select(CorporateAction).where(CorporateAction.kind == "split").order_by(CorporateAction.date.desc())
    return [{"id": a.id, "symbol": a.symbol, "date": a.date, "ratio": a.value} for a in db.scalars(q)]


@app.post("/api/splits", status_code=201)
def create_split(body: SplitIn, db: Session = Depends(get_db)):
    """For splits Yahoo applied to prices but never listed as an event."""
    with write_lock:
        if db.get(Holding, body.symbol) is None:
            raise HTTPException(404, "找不到持倉")
        fetcher.upsert_action(db, body.symbol, body.date, "split", body.ratio)
        _rebuild(db)
        db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ dashboard data

@app.get("/api/summary")
def get_summary(db: Session = Depends(get_db)):
    return _summary(db)


@app.get("/api/projection")
def get_projection(db: Session = Depends(get_db)):
    cfg = get_config(db)
    pos = ledger.position_rows(db, cfg)
    params = calculator.FireParams.from_config(cfg)
    today = ledger.today_tw()
    return {
        "today": today.isoformat(),
        "fire_target": calculator.fire_target(params),
        "series": calculator.project(params, pos["total_twd"], today),
    }


@app.get("/api/history")
def get_history(db: Session = Depends(get_db)):
    """Daily snapshots, nominal and in today's TWD."""
    cfg = get_config(db)
    today = ledger.today_tw()
    out = []
    for s in db.scalars(select(PortfolioSnapshot).order_by(PortfolioSnapshot.date)):
        d = date.fromisoformat(s.date)
        out.append(
            {
                "date": s.date,
                "total_value_twd": s.total_value_twd,
                "total_value_real": calculator.deflate(s.total_value_twd, cfg.inflation_rate, d, today),
                "total_value_usd": s.total_value_usd,
                "cash_twd": s.cash_twd,
                "fx_rate": s.fx_rate,
                "fx_ma200": s.fx_ma200,
                "coast_target_twd": s.coast_target_twd,
            }
        )
    return out


@app.get("/api/dividends")
def list_dividends(db: Session = Depends(get_db)):
    q = select(Dividend).order_by(Dividend.ex_date.desc())
    return [
        {
            "symbol": d.symbol, "ex_date": d.ex_date, "per_share": d.per_share,
            "shares_held": d.shares_held, "gross": d.gross, "tax_withheld": d.tax_withheld,
            "nhi_premium": d.nhi_premium, "net": d.net, "currency": d.currency,
        }
        for d in db.scalars(q)
    ]


@app.get("/api/status")
def get_status(db: Session = Depends(get_db)):
    rows = list(db.scalars(select(FetchStatus).order_by(FetchStatus.symbol)))
    ok_dates = [r.last_success_date for r in rows if r.last_success_date]
    return {
        "refreshing": _refresh_state["running"],
        "last_success_date": min(ok_dates) if ok_dates else None,
        "symbols": [
            {
                "symbol": r.symbol, "last_success_date": r.last_success_date,
                "last_attempt_at": r.last_attempt_at, "last_error": r.last_error,
            }
            for r in rows
        ],
        "errors": [r.symbol for r in rows if r.last_error],
        "fx_symbol": FX_SYMBOL,
    }


@app.post("/api/refresh", status_code=202)
def trigger_refresh():
    if _refresh_state["running"]:
        return {"started": False, "reason": "already running"}
    refresh_in_background()
    return {"started": True}


@app.get("/api/health")
def health():
    return {"ok": True}
