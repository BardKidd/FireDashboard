"""Valuation of fixed-payout savings agreements (FixedContract)."""
from __future__ import annotations

from datetime import date

from .models import FixedContract


def implied_monthly_rate(deposit: float, term: int, payout: float) -> float:
    """Monthly rate r where deposits at the start of each month grow to payout
    one month after the last deposit: D * ((1+r)^n - 1) / r * (1+r) = payout."""
    if deposit <= 0 or term <= 0 or payout <= deposit * term:
        return 0.0
    lo, hi = 1e-9, 1.0
    for _ in range(200):
        r = (lo + hi) / 2
        fv = deposit * ((1 + r) ** term - 1) / r * (1 + r)
        lo, hi = (r, hi) if fv < payout else (lo, r)
    return (lo + hi) / 2


def months_elapsed(c: FixedContract, day: date) -> int:
    """0 in the month of the first deposit."""
    y, m = (int(x) for x in c.start_month.split("-"))
    return (day.year - y) * 12 + day.month - m


def info(c: FixedContract, day: date) -> dict:
    m = months_elapsed(c, day)
    paid = max(0, min(m + 1, c.term_months))
    r = implied_monthly_rate(c.monthly_deposit, c.term_months, c.payout)
    matured = m >= c.term_months
    if m < 0:
        accrued = 0.0
    elif matured:
        accrued = c.payout
    else:
        accrued = sum(c.monthly_deposit * (1 + r) ** (m - k) for k in range(paid))
    deposited = paid * c.monthly_deposit
    value = accrued if c.valuation == "accrued" or matured else deposited
    y, mo = (int(x) for x in c.start_month.split("-"))
    end = y * 12 + mo - 1 + c.term_months  # payout month index
    return {
        "id": c.id,
        "name": c.name,
        "start_month": c.start_month,
        "monthly_deposit": c.monthly_deposit,
        "term_months": c.term_months,
        "payout": c.payout,
        "valuation": c.valuation,
        "closed": c.closed,
        "note": c.note,
        "paid_months": paid,
        "deposited": deposited,
        "accrued": accrued,
        "value": value,
        "matured": matured,
        "payout_month": f"{end // 12:04d}-{end % 12 + 1:02d}",
        "implied_annual_rate": (1 + r) ** 12 - 1,
    }


def value_on(c: FixedContract, day: date) -> float:
    return 0.0 if c.closed else info(c, day)["value"]
