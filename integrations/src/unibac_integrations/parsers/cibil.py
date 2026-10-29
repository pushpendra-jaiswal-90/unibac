"""CIBIL (bureau report) parser → `CibilSummary`."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, Field


class CibilSummary(BaseModel):
    score: int | None = None
    active_accounts: int = 0
    overdue_amount: Decimal = Field(default=Decimal(0))
    enquiries_last_6m: int = 0


class CibilParser:
    def parse(self, path: Path) -> CibilSummary:
        _ = path
        return CibilSummary()
