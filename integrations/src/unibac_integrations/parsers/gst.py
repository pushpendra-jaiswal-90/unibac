"""GST return parser.

Reads a GSTR-3B workbook (as downloaded from the GST portal) and returns the
summary the Rust `cam-builder` consumes:

    { avg_monthly_turnover, filing_regularity_pct, last_filed_period }

The GSTR-3B tab has one row per return period with at least these columns:

    Return Period | GSTIN | Filed On | Outward Taxable Supplies | IGST | CGST | SGST | Total Tax Paid

A `Filed On` cell containing the literal "NOT FILED" marks a missed period.
"""

from __future__ import annotations

import re
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook
from pydantic import BaseModel, Field

_REQUIRED = {"return period", "filed on", "outward taxable supplies"}
_PERIOD_RX = re.compile(r"(\d{1,2})[-/](\d{4})")  # MM-YYYY or MM/YYYY


class GstSummary(BaseModel):
    avg_monthly_turnover: Decimal = Field(default=Decimal(0))
    filing_regularity_pct: Decimal = Field(default=Decimal(0))
    last_filed_period: str | None = None
    periods_observed: int = 0


class GstParser:
    def parse(self, path: Path) -> GstSummary:
        wb = load_workbook(path, data_only=True, read_only=True)
        ws = _pick_sheet(wb)
        if ws is None:
            return GstSummary()

        header_row, col = _find_header(ws)
        if header_row is None:
            return GstSummary()

        turnovers: list[Decimal] = []
        filed = 0
        total = 0
        last_filed: date | None = None

        for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
            period = row[col["return period"]]
            if period is None:
                continue
            total += 1

            turnover = _to_decimal(row[col["outward taxable supplies"]])
            turnovers.append(turnover)

            filed_on = row[col["filed on"]]
            if _is_filed(filed_on):
                filed += 1
                pdate = _parse_period(period)
                if pdate and (last_filed is None or pdate > last_filed):
                    last_filed = pdate

        if total == 0:
            return GstSummary()

        avg = (sum(turnovers, Decimal(0)) / total).quantize(Decimal("0.01"))
        pct = (Decimal(filed) * 100 / Decimal(total)).quantize(Decimal("0.01"))
        return GstSummary(
            avg_monthly_turnover=avg,
            filing_regularity_pct=pct,
            last_filed_period=last_filed.strftime("%Y-%m") if last_filed else None,
            periods_observed=total,
        )


def _pick_sheet(wb):
    # Prefer a sheet named like GSTR-3B; fall back to the first that has required headers.
    for name in wb.sheetnames:
        if "3b" in name.lower():
            return wb[name]
    return wb.active


def _find_header(ws) -> tuple[int | None, dict[str, int]]:
    for row_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=10, values_only=True), start=1):
        labels = {str(c).strip().lower(): i for i, c in enumerate(row) if c is not None}
        if _REQUIRED.issubset(labels.keys()):
            return row_idx, labels
    return None, {}


def _is_filed(cell) -> bool:
    if cell is None:
        return False
    if isinstance(cell, (date, datetime)):
        return True
    s = str(cell).strip().upper()
    return bool(s) and "NOT FILED" not in s


def _parse_period(cell) -> date | None:
    if isinstance(cell, (date, datetime)):
        return date(cell.year, cell.month, 1)
    m = _PERIOD_RX.search(str(cell))
    if not m:
        return None
    try:
        return date(int(m.group(2)), int(m.group(1)), 1)
    except ValueError:
        return None


def _to_decimal(x) -> Decimal:
    if x is None or x == "":
        return Decimal(0)
    try:
        return Decimal(str(x))
    except Exception:
        return Decimal(0)


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python -m unibac_integrations.parsers.gst <path>", file=sys.stderr)
        raise SystemExit(2)
    print(GstParser().parse(Path(sys.argv[1])).model_dump_json(indent=2))


if __name__ == "__main__":
    main()
