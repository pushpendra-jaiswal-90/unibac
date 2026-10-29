"""Bank statement parser.

Produces the JSON shape consumed by `core/crates/cam-builder`:
    { avg_monthly_credit, avg_monthly_debit, bounce_count, min_eod_balance }
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, Field


class BankSummary(BaseModel):
    avg_monthly_credit: Decimal = Field(default=Decimal(0))
    avg_monthly_debit: Decimal = Field(default=Decimal(0))
    bounce_count: int = 0
    min_eod_balance: Decimal = Field(default=Decimal(0))


class BankStatementParser:
    """Parses a PDF/XLSX bank statement into a `BankSummary`.

    Implementation hooks:
      * PDF  -> `pdfplumber`
      * XLSX -> `openpyxl`
    Normalise narration into credit/debit/bounce categories, then aggregate.
    """

    def parse(self, path: Path) -> BankSummary:
        # TODO: real implementation. The stub lets the pipeline wire up
        # end-to-end against the Rust CAM builder.
        _ = path
        return BankSummary()
