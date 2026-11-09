from datetime import date

import pytest

from app import calculator as c

TODAY = date(2026, 11, 9)


def params(**kw):
    base = dict(
        birth_year=1995, birth_month=11, target_retire_age=55, annual_expense_twd=600_000,
        swr=0.04, expected_nominal_return=0.085, inflation_rate=0.025,
        monthly_contribution_twd=30_000, contribution_indexed=True, stress_drop=0.2,
    )
    base.update(kw)
    return c.FireParams(**base)


def test_real_return_and_target():
    assert c.real_return(0.085, 0.025) == pytest.approx(1.085 / 1.025 - 1)
    assert c.fire_target(params()) == pytest.approx(15_000_000)


def test_months_remaining_uses_birth_month():
    assert c.months_remaining(params(), TODAY) == 24 * 12  # turned 31 this month
    assert c.months_remaining(params(birth_month=12), TODAY) == 24 * 12 + 1


def test_coast_target_matches_annual_formula():
    p = params()
    rr = c.real_return(0.085, 0.025)
    assert c.coast_target(p, 24 * 12) == pytest.approx(15_000_000 / (1 + rr) ** 24)


def test_time_to_coast_achieved():
    p = params()
    big = c.coast_target(p, c.months_remaining(p, TODAY)) * 1.01
    r = c.time_to_coast(p, big, TODAY)
    assert r["status"] == "achieved" and r["months"] == 0


def test_time_to_coast_reachable_and_monotone():
    p = params()
    r = c.time_to_coast(p, 1_000_000, TODAY)
    assert r["status"] == "reachable"
    series = c.project(p, 1_000_000, TODAY)
    t = r["months"]
    assert series[t]["with_contribution"] >= series[t]["coast_target"]
    assert series[t - 1]["with_contribution"] < series[t - 1]["coast_target"]


def test_time_to_coast_unreachable_reports_gap():
    p = params(monthly_contribution_twd=0, birth_year=1975)
    r = c.time_to_coast(p, 100_000, TODAY)
    assert r["status"] == "unreachable"
    assert r["gap_at_retirement"] > 0


def test_retirement_age_already_passed():
    p = params(birth_year=1960)
    assert c.months_remaining(p, TODAY) == 0
    assert c.coast_target(p, 0) == pytest.approx(c.fire_target(p))
    assert c.time_to_coast(p, 20_000_000, TODAY)["status"] == "achieved"


def test_non_indexed_contribution_is_slower():
    a = c.time_to_coast(params(), 1_000_000, TODAY)["months"]
    b = c.time_to_coast(params(contribution_indexed=False), 1_000_000, TODAY)["months"]
    assert b >= a


def test_monthly_income_if_stop():
    p = params()
    rr = c.real_return(0.085, 0.025)
    assert c.monthly_income_if_stop(p, 5_000_000, TODAY) == pytest.approx(5_000_000 * (1 + rr) ** 24 * 0.04 / 12)


def test_stress_and_cushion():
    beta = c.portfolio_beta([(800, 1.0), (200, 0.0)])
    assert beta == pytest.approx(0.8)
    s = c.stress_test(1000, 600, beta, 0.2)
    assert s["stressed_value"] == pytest.approx(1000 * (1 - 0.16))
    assert s["max_market_drop"] == pytest.approx((1 - 0.6) / 0.8)
    assert c.stress_test(500, 600, 1.0, 0.2)["max_market_drop"] is None
    assert c.stress_test(1000, 600, 0.0, 0.2)["max_market_drop"] == 1.0
