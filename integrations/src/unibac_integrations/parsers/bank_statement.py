"""Bank statement parser.

Consumes an Indian retail-bank account statement (HDFC/ICICI-style) in `.xlsx`
form and emits the JSON shape the Rust `cam-builder` expects:

    { avg_monthly_credit, avg_monthly_debit, bounce_count, min_eod_balance }

The sandbox statements have 7 known columns:

    Date | Narration | Chq./Ref.No. | Value Dt | Withdrawal Amt. | Deposit Amt. | Closing Balance

The header row is located dynamically (banks shift the header depending on
how much metadata they prepend), so other NBFC exports with the same column
labels should parse without changes.
"""

from __future__ import annotations

import re
import sys
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook
from pydantic import BaseModel, Field

_BOUNCE_RX = re.compile(r"(RETURN|BOUNCE|INSUFFICIENT|REVERSAL|DISHONOUR)", re.IGNORECASE)
_REQUIRED_HEADERS = {"date", "narration", "withdrawal amt.", "deposit amt.", "closing balance"}


class BankSummary(BaseModel):
    avg_monthly_credit: Decimal = Field(default=Decimal(0))
    avg_monthly_debit: Decimal = Field(default=Decimal(0))
    bounce_count: int = 0
    min_eod_balance: Decimal = Field(default=Decimal(0))
    months_observed: int = 0


class BankStatementParser:
    def parse(self, path: Path) -> BankSummary:
        wb = load_workbook(path, data_only=True, read_only=True)
        ws = wb.active

        header_row_idx, col_idx = _find_header(ws)
        if header_row_idx is None:
            return BankSummary()

        total_credit = Decimal(0)
        total_debit  = Decimal(0)
        bounces      = 0
        min_bal: Decimal | None = None
        months: set[str] = set()

        for row in ws.iter_rows(min_row=header_row_idx + 1, values_only=True):
            date_cell  = row[col_idx["date"]]
            narration  = (row[col_idx["narration"]] or "")
            withdrawal = _to_decimal(row[col_idx["withdrawal amt."]])
            deposit    = _to_decimal(row[col_idx["deposit amt."]])
            balance    = _to_decimal(row[col_idx["closing balance"]])

            if date_cell is None:
                continue

            total_credit += deposit
            total_debit  += withdrawal
            if min_bal is None or balance < min_bal:
                min_bal = balance
            if _BOUNCE_RX.search(str(narration)):
                bounces += 1

            # Collect unique YYYY-MM for the monthly denominator.
            m = _month_key(date_cell)
            if m:
                months.add(m)

        n_months = max(len(months), 1)
        return BankSummary(
            avg_monthly_credit = (total_credit / n_months).quantize(Decimal("0.01")),
            avg_monthly_debit  = (total_debit  / n_months).quantize(Decimal("0.01")),
            bounce_count       = bounces,
            min_eod_balance    = (min_bal or Decimal(0)).quantize(Decimal("0.01")),
            months_observed    = len(months),
        )


def _find_header(ws) -> tuple[int | None, dict[str, int]]:
    """Scan the first 30 rows for the data-table header; return 1-based row + col index."""
    for row_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=30, values_only=True), start=1):
        labels = {str(c).strip().lower(): i for i, c in enumerate(row) if c is not None}
        if _REQUIRED_HEADERS.issubset(labels.keys()):
            return row_idx, labels
    return None, {}


def _to_decimal(x) -> Decimal:
    if x is None or x == "":
        return Decimal(0)
    if isinstance(x, Decimal):
        return x
    try:
        return Decimal(str(x))
    except Exception:
        return Decimal(0)


def _month_key(x) -> str | None:
    if hasattr(x, "year") and hasattr(x, "month"):
        return f"{x.year:04d}-{x.month:02d}"
    s = str(x)
    # dd/mm/yyyy
    m = re.match(r"\d{1,2}/(\d{1,2})/(\d{4})", s)
    if m:
        return f"{m.group(2)}-{int(m.group(1)):02d}"
    return None


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python -m unibac_integrations.parsers.bank_statement <path>", file=sys.stderr)
        raise SystemExit(2)
    print(BankStatementParser().parse(Path(sys.argv[1])).model_dump_json(indent=2))


if __name__ == "__main__":
    main()
