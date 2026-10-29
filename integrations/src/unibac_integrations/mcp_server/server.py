"""LBI MCP server.

Exposes a small set of tools so an MCP-aware client (Claude, Claude Code, etc.)
can drive the parsing + CAM pipeline end-to-end:

    * parse_bank_statement
    * parse_cibil
    * parse_gst
    * build_cam           (shells out to `lbi-core cam`)
    * build_worklist      (shells out to `lbi-core worklist`)

Transport: stdio by default (how MCP clients spawn tool servers).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from unibac_integrations.parsers import (
    BankStatementParser,
    CibilParser,
    GstParser,
)

mcp = FastMCP("lbi")

CORE_BIN = os.environ.get("LBI_CORE_BINARY", "lbi-core")


@mcp.tool()
def parse_bank_statement(path: str) -> dict[str, Any]:
    """Parse a bank-statement PDF/XLSX into the canonical summary JSON."""
    return BankStatementParser().parse(Path(path)).model_dump(mode="json")


@mcp.tool()
def parse_cibil(path: str) -> dict[str, Any]:
    """Parse a CIBIL report PDF into the canonical summary JSON."""
    return CibilParser().parse(Path(path)).model_dump(mode="json")


@mcp.tool()
def parse_gst(path: str) -> dict[str, Any]:
    """Parse GST return exports (JSON/XLSX) into the canonical summary JSON."""
    return GstParser().parse(Path(path)).model_dump(mode="json")


@mcp.tool()
def build_cam(bank_json: str, cibil_json: str, gst_json: str, out_path: str) -> dict[str, Any]:
    """Invoke `lbi-core cam` to produce a Credit Appraisal Memo JSON file."""
    subprocess.run(
        [CORE_BIN, "cam", "--bank", bank_json, "--cibil", cibil_json, "--gst", gst_json, "--out", out_path],
        check=True,
    )
    return json.loads(Path(out_path).read_text())


@mcp.tool()
def build_worklist(snapshots: str, repayments: str, activity: str, limit: int = 100) -> list[dict[str, Any]]:
    """Invoke `lbi-core worklist` and return the prioritised worklist."""
    result = subprocess.run(
        [
            CORE_BIN, "worklist",
            "--snapshots", snapshots,
            "--repayments", repayments,
            "--activity", activity,
            "--limit", str(limit),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout or "[]")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
