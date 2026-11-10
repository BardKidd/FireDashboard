from datetime import date

import pytest

from app import contracts
from app.models import FixedContract


def family(**kw):
    base = dict(id=1, name="家人", start_month="2021-09", monthly_deposit=10000, term_months=120,
                payout=2_000_000, valuation="accrued", closed=False, note=None)
    base.update(kw)
    return FixedContract(**base)


def test_paid_months_and_deposited():
    i = contracts.info(family(), date(2026, 11, 10))
    assert i["paid_months"] == 63
    assert i["deposited"] == 630_000
    assert i["payout_month"] == "2031-09"


def test_accrued_reaches_payout_at_maturity():
    c = family()
    r = contracts.implied_monthly_rate(10000, 120, 2_000_000)
    assert (1 + r) ** 12 - 1 == pytest.approx(0.0986, abs=1e-3)
    before = contracts.info(c, date(2031, 8, 15))
    assert before["accrued"] == pytest.approx(2_000_000 / (1 + r), rel=1e-6)
    assert contracts.info(c, date(2031, 9, 1))["value"] == 2_000_000


def test_valuation_modes_and_closed():
    d = date(2026, 11, 10)
    assert contracts.info(family(valuation="deposited"), d)["value"] == 630_000
    assert contracts.info(family(), d)["value"] > 630_000
    assert contracts.value_on(family(closed=True), d) == 0
    assert contracts.info(family(), date(2021, 8, 1))["value"] == 0
