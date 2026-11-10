from datetime import date

import pytest

from app import contracts
from app.models import FixedContract


def family(**kw):
    base = dict(id=1, name="定期存款", start_month="2024-01", monthly_deposit=5000, term_months=60,
                payout=350_000, valuation="accrued", closed=False, note=None)
    base.update(kw)
    return FixedContract(**base)


def test_paid_months_and_deposited():
    i = contracts.info(family(), date(2026, 11, 10))
    assert i["paid_months"] == 35
    assert i["deposited"] == 175_000
    assert i["payout_month"] == "2029-01"


def test_accrued_reaches_payout_at_maturity():
    c = family()
    r = contracts.implied_monthly_rate(5000, 60, 350_000)
    assert (1 + r) ** 12 - 1 == pytest.approx(0.0610, abs=1e-3)
    before = contracts.info(c, date(2028, 12, 15))
    assert before["accrued"] == pytest.approx(350_000 / (1 + r), rel=1e-6)
    assert contracts.info(c, date(2029, 1, 1))["value"] == 350_000


def test_valuation_modes_and_closed():
    d = date(2026, 11, 10)
    assert contracts.info(family(valuation="deposited"), d)["value"] == 175_000
    assert contracts.info(family(), d)["value"] > 175_000
    assert contracts.value_on(family(closed=True), d) == 0
    assert contracts.info(family(), date(2023, 12, 1))["value"] == 0
