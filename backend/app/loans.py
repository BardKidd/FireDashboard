"""Amortising loans (Loan): remaining principal on any day, and the schedule
the Coast FIRE projection needs.

Payments are monthly and equal; payment k (k = 1..term) falls in the k-th
calendar month after the month the money arrived and counts from the first
day of that month.
"""
from __future__ import annotations

from datetime import date

from .models import Loan


def annuity_payment(principal: float, annual_rate: float, term: int) -> float:
    if term <= 0:
        return 0.0
    r = annual_rate / 12
    if r <= 0:
        return principal / term
    return principal * r / (1 - (1 + r) ** -term)


def payment_of(loan: Loan) -> float:
    return loan.payment if loan.payment and loan.payment > 0 else annuity_payment(
        loan.principal, loan.annual_rate, loan.term_months
    )


def _month_index(d: date) -> int:
    return d.year * 12 + d.month - 1


def payments_made(loan: Loan, day: date) -> int:
    start = date.fromisoformat(loan.start_date)
    return max(0, min(loan.term_months, _month_index(day) - _month_index(start)))


def balance_after(loan: Loan, k: int) -> float:
    """Remaining principal after k payments (0 once the loan is paid off)."""
    if k >= loan.term_months:
        return 0.0
    r = loan.annual_rate / 12
    pay = payment_of(loan)
    b = loan.principal
    for _ in range(k):
        b = b * (1 + r) - pay
        if b <= 0:
            return 0.0
    return b


def payoff_count(loan: Loan) -> int:
    """Number of payments until the balance reaches 0 (at most the term)."""
    r = loan.annual_rate / 12
    pay = payment_of(loan)
    b = loan.principal
    for k in range(1, loan.term_months + 1):
        b = b * (1 + r) - pay
        if b <= 0.5:
            return k
    return loan.term_months


def balance_on(loan: Loan, day: date) -> float:
    if loan.closed or day < date.fromisoformat(loan.start_date):
        return 0.0
    return balance_after(loan, payments_made(loan, day))


def _ym(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def info(loan: Loan, day: date) -> dict:
    pay = payment_of(loan)
    k = payments_made(loan, day)
    n = payoff_count(loan)
    start = date.fromisoformat(loan.start_date)
    balance = balance_on(loan, day)
    r = loan.annual_rate / 12
    interest_now = balance * r if balance > 0 else 0.0
    return {
        "id": loan.id,
        "name": loan.name,
        "start_date": loan.start_date,
        "principal": loan.principal,
        "annual_rate": loan.annual_rate,
        "term_months": loan.term_months,
        "payment": loan.payment,
        "redirect_after": loan.redirect_after,
        "closed": loan.closed,
        "note": loan.note,
        "monthly_payment": pay,
        "paid_months": min(k, n),
        "payoff_months": n,
        "balance": balance,
        "repaid_principal": loan.principal - balance if not loan.closed else loan.principal,
        "total_interest": max(0.0, pay * n - loan.principal),
        "next_interest": interest_now,
        "next_principal": min(balance, max(0.0, pay - interest_now)),
        "first_payment_month": _ym(_month_index(start) + 1),
        "payoff_month": _ym(_month_index(start) + n),
        "paid_off": loan.closed or balance <= 0,
    }


def total_on(loans: list[Loan], day: date) -> float:
    return sum(balance_on(l, day) for l in loans)


def plan(loans: list[Loan], today: date, months: int) -> tuple[list[float], list[float]]:
    """For t = 0..months (t = months from the first of today's month):
    nominal remaining principal, and the nominal payment freed up for
    investing that month because a loan was paid off before it."""
    base = _month_index(today)
    debt = [0.0] * (months + 1)
    freed = [0.0] * (months + 1)
    for loan in loans:
        if loan.closed:
            continue
        start = _month_index(date.fromisoformat(loan.start_date))
        n = payoff_count(loan)
        pay = payment_of(loan)
        for t in range(months + 1):
            idx = base + t
            if idx < start:
                continue
            k = min(loan.term_months, idx - start)
            debt[t] += balance_after(loan, k)
            if loan.redirect_after and idx - start > n:
                freed[t] += pay
    return debt, freed
