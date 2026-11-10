"""Import initial holdings and fixed contracts from a JSON file.

    docker compose exec backend python -m app.seed /data/initial_holdings.json

Format:
{
  "date": "2026-11-10",                      # default start date for holdings
  "holdings": [
    {"symbol": "0050", "name": "元大台灣50", "shares": 1000, "avg_cost": 50.1,
     "asset_type": "equity", "date": "2026-11-10", "note": "初始持倉"}
  ],
  "contracts": [
    {"name": "家人約定存款", "start_month": "2021-09", "monthly_deposit": 10000,
     "term_months": 120, "payout": 2000000}
  ]
}

Holdings already present (same normalised symbol, not archived) and contracts
with an existing name are skipped, so running it twice is safe.
"""
from __future__ import annotations

import json
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import fetcher, ledger
from .models import FixedContract, Holding

ASSET_BETA = {"equity": 1.0, "leveraged": 2.0, "bond": 0.0}


def import_data(db: Session, data: dict) -> dict:
    default_day = data.get("date") or ledger.today_tw().isoformat()
    report: dict[str, list] = {"added": [], "skipped": [], "errors": [], "contracts": []}
    for item in data.get("holdings", []):
        raw = str(item["symbol"])
        try:
            symbol = fetcher.normalize_symbol(raw)
        except fetcher.FetchError as exc:
            report["errors"].append(f"{raw}: {exc}")
            continue
        h = db.get(Holding, symbol)
        if h is not None and not h.archived and h.shares > 0:
            report["skipped"].append(symbol)
            continue
        meta = fetcher.guess_meta(symbol)
        if item.get("asset_type"):
            meta["asset_type"] = item["asset_type"]
            meta["stress_beta"] = ASSET_BETA.get(item["asset_type"], 1.0)
        if item.get("stress_beta") is not None:
            meta["stress_beta"] = float(item["stress_beta"])
        if h is None:
            h = Holding(symbol=symbol, shares=0.0, **meta)
            db.add(h)
        h.archived = False
        h.name = item.get("name") or h.name or fetcher.lookup_name(symbol)
        if item.get("avg_cost") is not None:
            h.avg_cost = float(item["avg_cost"])
        db.flush()
        shares = float(item.get("shares") or 0)
        if shares > 0:
            ledger.add_log(
                db, symbol, item.get("date") or default_day, "adjust",
                delta=shares, note=item.get("note") or "初始持倉",
            )
        report["added"].append(symbol)
    existing = {c.name for c in db.scalars(select(FixedContract))}
    for c in data.get("contracts", []):
        if c["name"] in existing:
            report["skipped"].append(c["name"])
            continue
        db.add(
            FixedContract(
                name=c["name"],
                start_month=c["start_month"],
                monthly_deposit=float(c["monthly_deposit"]),
                term_months=int(c["term_months"]),
                payout=float(c["payout"]),
                valuation=c.get("valuation", "accrued"),
                note=c.get("note"),
            )
        )
        report["contracts"].append(c["name"])
    db.flush()
    ledger.rebuild_all(db)
    db.commit()
    return report


def main(path: str) -> None:
    from .database import SessionLocal, init_db, write_lock

    init_db()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    with write_lock, SessionLocal() as db:
        report = import_data(db, data)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("抓取報價中…")
    print(json.dumps(fetcher.refresh(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("用法：python -m app.seed <json 檔路徑>")
    main(sys.argv[1])
