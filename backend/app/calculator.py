"""Coast FIRE engine (SPEC.md section 5). Pure functions, no database access.

Every projection is in today's TWD purchasing power, so all growth uses the
real return.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class FireParams:
    birth_year: int
    birth_month: int
    target_retire_age: int
    annual_expense_twd: float
    swr: float
    expected_nominal_return: float
    inflation_rate: float
    monthly_contribution_twd: float
    contribution_indexed: bool = True
    stress_drop: float = 0.20

    @classmethod
    def from_config(cls, cfg) -> "FireParams":
        return cls(
            birth_year=cfg.birth_year,
            birth_month=cfg.birth_month,
            target_retire_age=cfg.target_retire_age,
            annual_expense_twd=cfg.annual_expense_twd,
            swr=cfg.swr,
            expected_nominal_return=cfg.expected_nominal_return,
            inflation_rate=cfg.inflation_rate,
            monthly_contribution_twd=cfg.monthly_contribution_twd,
            contribution_indexed=cfg.contribution_indexed,
            stress_drop=cfg.stress_drop,
        )


# ---------------------------------------------------------------- 5.1 basics

def real_return(nominal: float, inflation: float) -> float:
    return (1 + nominal) / (1 + inflation) - 1


def monthly_rate(r_real: float) -> float:
    return (1 + r_real) ** (1 / 12) - 1


def fire_target(p: FireParams) -> float:
    if p.swr <= 0:
        raise ValueError("SWR must be positive")
    return p.annual_expense_twd / p.swr


def age_in_months(p: FireParams, today: date) -> int:
    return (today.year - p.birth_year) * 12 + (today.month - p.birth_month)


def months_remaining(p: FireParams, today: date) -> int:
    return max(0, p.target_retire_age * 12 - age_in_months(p, today))


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


# ---------------------------------------------------------------- 5.3 coast

def coast_target(p: FireParams, months_left: int) -> float:
    rm = monthly_rate(real_return(p.expected_nominal_return, p.inflation_rate))
    return fire_target(p) / (1 + rm) ** months_left


def contribution_at(p: FireParams, t: int) -> float:
    """Real (today-TWD) contribution made in month t (t >= 1)."""
    if p.contribution_indexed:
        return p.monthly_contribution_twd
    return p.monthly_contribution_twd / (1 + p.inflation_rate) ** (t / 12)


# ---------------------------------------------------------------- 5.4 / 5.7 projection

def project(p: FireParams, p0: float, today: date) -> list[dict]:
    """Month-by-month series from now to retirement (inclusive)."""
    rm = monthly_rate(real_return(p.expected_nominal_return, p.inflation_rate))
    n = months_remaining(p, today)
    target = fire_target(p)
    start = date(today.year, today.month, 1)
    out = []
    with_c = p0
    for t in range(n + 1):
        if t > 0:
            with_c = with_c * (1 + rm) + contribution_at(p, t)
        out.append(
            {
                "t": t,
                "month": add_months(start, t).strftime("%Y-%m"),
                "coast_target": target / (1 + rm) ** (n - t),
                "no_contribution": p0 * (1 + rm) ** t,
                "with_contribution": with_c,
            }
        )
    return out


def time_to_coast(p: FireParams, p0: float, today: date) -> dict:
    series = project(p, p0, today)
    n = len(series) - 1
    for row in series:
        if row["with_contribution"] >= row["coast_target"]:
            if row["t"] == 0:
                return {"status": "achieved", "months": 0, "month": row["month"]}
            return {"status": "reachable", "months": row["t"], "month": row["month"]}
    last = series[-1]
    return {
        "status": "unreachable",
        "months": None,
        "month": None,
        "gap_at_retirement": fire_target(p) - last["with_contribution"],
        "retire_month": last["month"] if n >= 0 else None,
    }


# ---------------------------------------------------------------- 5.5 stop-now income

def monthly_income_if_stop(p: FireParams, p0: float, today: date) -> float:
    rr = real_return(p.expected_nominal_return, p.inflation_rate)
    n = months_remaining(p, today)
    return p0 * (1 + rr) ** (n / 12) * p.swr / 12


# ---------------------------------------------------------------- 5.6 stress

def portfolio_beta(values_and_betas: Iterable[tuple[float, float]]) -> float:
    pairs = list(values_and_betas)
    total = sum(v for v, _ in pairs)
    if total <= 0:
        return 0.0
    return sum(v * b for v, b in pairs) / total


def stress_test(p0: float, coast0: float, beta: float, drop: float) -> dict:
    progress = p0 / coast0 if coast0 > 0 else None
    stressed_value = p0 * (1 - drop * beta)
    stressed_progress = stressed_value / coast0 if coast0 > 0 else None
    if p0 <= 0 or coast0 <= 0 or p0 < coast0:
        cushion = None  # not yet in the safe zone
    elif beta <= 0:
        cushion = 1.0  # nothing in the portfolio moves with the market
    else:
        cushion = min(1.0, (1 - coast0 / p0) / beta)
    return {
        "beta": beta,
        "drop": drop,
        "progress": progress,
        "stressed_value": stressed_value,
        "stressed_progress": stressed_progress,
        "max_market_drop": cushion,
    }


# ---------------------------------------------------------------- summary

def summary(p: FireParams, p0: float, beta: float, today: date) -> dict:
    n = months_remaining(p, today)
    coast0 = coast_target(p, n)
    rr = real_return(p.expected_nominal_return, p.inflation_rate)
    return {
        "today": today.isoformat(),
        "age_years": age_in_months(p, today) / 12,
        "months_remaining": n,
        "real_return": rr,
        "fire_target": fire_target(p),
        "coast_target": coast0,
        "total_assets": p0,
        "progress": p0 / coast0 if coast0 > 0 else None,
        "time_to_coast": time_to_coast(p, p0, today),
        "monthly_income_if_stop": monthly_income_if_stop(p, p0, today),
        "stress": stress_test(p0, coast0, beta, p.stress_drop),
    }


def deflate(value: float, inflation: float, from_day: date, to_day: date) -> float:
    """Express a nominal TWD amount from from_day in to_day purchasing power."""
    years = (to_day - from_day).days / 365.25
    return value * (1 + inflation) ** years
