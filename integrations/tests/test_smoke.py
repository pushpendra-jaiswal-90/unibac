"""Smoke tests that run the real parsers against the committed sample files."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from unibac_integrations.parsers import BankStatementParser, CibilParser, GstParser

SAMPLE = Path(__file__).resolve().parents[2] / "sample" / "applicants"


def _needs_samples() -> None:
    if not SAMPLE.exists():
        pytest.skip("sample/ data not generated — run `lbi-sandbox-gen`")


def test_bank_statement_approves_app001() -> None:
    _needs_samples()
    s = BankStatementParser().parse(SAMPLE / "APP001" / "bank_statement.xlsx")
    assert s.bounce_count == 0
    assert s.avg_monthly_credit > Decimal("500000")
    assert s.min_eod_balance > Decimal(0)
    assert s.months_observed == 6


def test_bank_statement_flags_app003() -> None:
    _needs_samples()
    s = BankStatementParser().parse(SAMPLE / "APP003" / "bank_statement.xlsx")
    assert s.bounce_count >= 5
    assert s.min_eod_balance < Decimal(0)


def test_cibil_scores_rank_correctly() -> None:
    _needs_samples()
    s1 = CibilParser().parse(SAMPLE / "APP001" / "cibil_report.pdf")
    s2 = CibilParser().parse(SAMPLE / "APP002" / "cibil_report.pdf")
    s3 = CibilParser().parse(SAMPLE / "APP003" / "cibil_report.pdf")
    assert s1.score and s2.score and s3.score
    assert s1.score > s2.score > s3.score
    assert s1.overdue_amount == Decimal(0)
    assert s3.overdue_amount > Decimal(0)
    assert s1.enquiries_last_6m < s3.enquiries_last_6m


def test_gst_filing_regularity_decreases_across_profiles() -> None:
    _needs_samples()
    g1 = GstParser().parse(SAMPLE / "APP001" / "gstr3b.xlsx")
    g3 = GstParser().parse(SAMPLE / "APP003" / "gstr3b.xlsx")
    assert g1.filing_regularity_pct > g3.filing_regularity_pct
    assert g1.avg_monthly_turnover > g3.avg_monthly_turnover
    assert g1.last_filed_period is not None
