"""GST return parser → `GstSummary`."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, Field


class GstSummary(BaseModel):
    avg_monthly_turnover: Decimal = Field(default=Decimal(0))
    filing_regularity_pct: Decimal = Field(default=Decimal(0))
    last_filed_period: str | None = None


class GstParser:
    def parse(self, path: Path) -> GstSummary:
        _ = path
        return GstSummary()
