"""CIBIL (TransUnion) report parser.

Extracts the aggregates the Rust `cam-builder` consumes:

    { score, active_accounts, overdue_amount, enquiries_last_6m }

The sandbox PDF layout mirrors a real CIBIL consumer credit information
report: a `CIBIL SCORE` panel, an `Account Information` table with an
`Overdue` column, and an `Enquiry Information (last 6 months)` table.
Each section is detected textually so the parser tolerates small layout
drift between report versions.
"""

from __future__ import annotations

import re
import sys
from decimal import Decimal
from pathlib import Path

import pdfplumber
from pydantic import BaseModel, Field

_SCORE_RX = re.compile(r"CIBIL\s+SCORE\s+(\d{3})")
_INT_RX   = re.compile(r"[\d,]+")


class CibilSummary(BaseModel):
    score: int | None = None
    active_accounts: int = 0
    overdue_amount: Decimal = Field(default=Decimal(0))
    enquiries_last_6m: int = 0


class CibilParser:
    def parse(self, path: Path) -> CibilSummary:
        tables: list[list[list[str]]] = []
        text_parts: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
                tables.extend(page.extract_tables() or [])

        text = "\n".join(text_parts)

        score = None
        m = _SCORE_RX.search(text)
        if m:
            score = int(m.group(1))

        active_accounts = 0
        overdue_amount  = Decimal(0)
        enquiries       = 0

        for tbl in tables:
            if not tbl:
                continue
            header = [(_norm(c)) for c in tbl[0]]
            data_rows = tbl[1:]

            # Account Information table — has an "Overdue" column.
            if "overdue" in header and "lender" in header:
                overdue_idx = header.index("overdue")
                active_accounts += len(data_rows)
                for r in data_rows:
                    if overdue_idx < len(r):
                        overdue_amount += _to_decimal(r[overdue_idx])

            # Enquiry Information table — has date + enquiring member.
            if "enquiring member" in header or "purpose" in header:
                enquiries += len(data_rows)

        return CibilSummary(
            score=score,
            active_accounts=active_accounts,
            overdue_amount=overdue_amount.quantize(Decimal("0.01")),
            enquiries_last_6m=enquiries,
        )


def _norm(x) -> str:
    return (x or "").strip().lower()


def _to_decimal(x) -> Decimal:
    if x is None:
        return Decimal(0)
    s = str(x)
    m = _INT_RX.search(s.replace(",", ""))
    if not m:
        return Decimal(0)
    try:
        return Decimal(m.group(0).replace(",", ""))
    except Exception:
        return Decimal(0)


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python -m unibac_integrations.parsers.cibil <path>", file=sys.stderr)
        raise SystemExit(2)
    print(CibilParser().parse(Path(sys.argv[1])).model_dump_json(indent=2))


if __name__ == "__main__":
    main()
