from datetime import date

import pytest

from app import calculator as c
from app import loans
from app.models import Loan

from .test_calculator import params

TODAY = date(2026, 11, 12)


def loan(**kw):
    base = dict(id=1, name="信貸", start_date="2026-01-10", principal=1_000_000, annual_rate=0.03,
                term_months=84, payment=None, redirect_after=True, closed=False, note=None)
    base.update(kw)
    return Loan(**base)


def test_annuity_payment():
    assert loans.annuity_payment(1_000_000, 0.03, 84) == pytest.approx(13_213.3, abs=1)
    assert loans.annuity_payment(120_000, 0, 12) == pytest.approx(10_000)


def test_balance_follows_schedule():
    l = loan()
    assert loans.balance_on(l, date(2026, 1, 31)) == pytest.approx(1_000_000)  # no payment yet
    # Feb 2026 is payment 1; Nov 2026 is payment 10.
    assert loans.payments_made(l, TODAY) == 10
    b10 = loans.balance_after(l, 10)
    assert loans.balance_on(l, TODAY) == pytest.approx(b10)
    assert 880_000 < b10 < 900_000
    assert loans.balance_on(l, date(2033, 1, 1)) == 0  # 84 payments done
    assert loans.balance_on(l, date(2025, 12, 31)) == 0  # before the money arrived
    assert loans.balance_on(loan(closed=True), TODAY) == 0


def test_info_totals():
    i = loans.info(loan(), TODAY)
    assert i["first_payment_month"] == "2026-02"
    assert i["payoff_month"] == "2033-01"
    assert i["total_interest"] == pytest.approx(13_213.3 * 84 - 1_000_000, abs=100)
    assert i["next_interest"] + i["next_principal"] == pytest.approx(i["monthly_payment"])


def test_bigger_payment_pays_off_early():
    i = loans.info(loan(payment=20_000), TODAY)
    assert i["payoff_months"] < 84
    assert loans.balance_after(loan(payment=20_000), i["payoff_months"]) == 0


def test_plan_debt_and_freed_payment():
    debt, freed = loans.plan([loan()], TODAY, 120)
    assert debt[0] == pytest.approx(loans.balance_on(loan(), TODAY))
    assert debt[-1] == 0
    # Payoff in 2033-01 (t = 74); the payment is invested from the month after.
    assert freed[74] == 0 and freed[75] == pytest.approx(loans.payment_of(loan()))
    _, freed2 = loans.plan([loan(redirect_after=False)], TODAY, 120)
    assert sum(freed2) == 0


def test_projection_counts_debt_once():
    p = params(monthly_contribution_twd=0)
    debt, freed = loans.plan([loan(redirect_after=False)], TODAY, c.months_remaining(p, TODAY))
    plan = c.DebtPlan(debt, freed)
    gross = c.project(p, 4_000_000, TODAY)
    net = c.project(p, 4_000_000, TODAY, plan)
    assert net[0]["with_contribution"] == pytest.approx(4_000_000 - debt[0])
    # Once the loan is repaid, net worth equals the gross projection again.
    assert net[-1]["with_contribution"] == pytest.approx(gross[-1]["with_contribution"])


def test_summary_and_stress_use_net_worth():
    p = params()
    debt, freed = loans.plan([loan()], TODAY, c.months_remaining(p, TODAY))
    plan = c.DebtPlan(debt, freed)
    s = c.summary(p, 4_000_000, 1.0, TODAY, plan)
    assert s["debt"] == pytest.approx(debt[0])
    assert s["net_worth"] == pytest.approx(4_000_000 - debt[0])
    assert s["progress"] == pytest.approx(s["net_worth"] / s["coast_target"])
    st = s["stress"]
    assert st["stressed_value"] == pytest.approx(4_000_000 * 0.8 - debt[0])
    assert st["net_beta"] > 1


def test_borrowing_to_invest_does_not_move_progress():
    p = params()
    n = c.months_remaining(p, TODAY)
    new = loan(start_date="2026-11-12")
    debt, freed = loans.plan([new], TODAY, n)
    before = c.summary(p, 3_000_000, 1.0, TODAY)
    after = c.summary(p, 4_000_000, 1.0, TODAY, c.DebtPlan(debt, freed))
    assert after["progress"] == pytest.approx(before["progress"])
    assert after["stress"]["stressed_progress"] < before["stress"]["stressed_progress"]


def test_loan_api(client):
    body = {"name": "信貸", "start_date": "2026-01-10", "principal": 1_000_000, "annual_rate": 0.03, "term_months": 84}
    r = client.post("/api/loans", json=body)
    assert r.status_code == 201, r.text
    lid = r.json()["id"]
    assert client.get("/api/summary").json()["debt"] > 0
    bad = dict(body, payment=1000)  # less than the interest
    assert client.put(f"/api/loans/{lid}", json=bad).status_code == 400
    assert client.put(f"/api/loans/{lid}", json=dict(body, closed=True)).json()["balance"] == 0
    assert client.get("/api/summary").json()["debt"] == 0
    assert client.delete(f"/api/loans/{lid}").status_code == 200
    assert client.get("/api/loans").json() == []
