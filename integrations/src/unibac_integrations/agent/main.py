"""LBI underwriting agent.

A thin loop that lets Claude (claude-opus-4-7 by default) call the LBI MCP
server tools to:
  * parse bank-statement / CIBIL / GST files for an applicant,
  * build a CAM,
  * surface a recommendation (approve / refer / decline) with rationale.

Prompt-caching is on by default — the system prompt and tool list rarely
change, so we mark the system block as `cache_control: ephemeral`.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from anthropic import Anthropic

MODEL = os.environ.get("LBI_AGENT_MODEL", "claude-opus-4-7")

SYSTEM_PROMPT = """\
You are the Unibac underwriting agent for a vehicle-finance NBFC.

Your job for each applicant:
  1. Parse the supplied bank statement, CIBIL report and GST return using the
     `parse_*` tools.
  2. Save each parsed JSON to a temp path (ask the user if unsure).
  3. Call `build_cam` to produce the Credit Appraisal Memo.
  4. Summarise the CAM: decision, top three rationale points, and any missing
     data that forced a REFER.

Rules:
  * Never fabricate numbers that the parsers did not return.
  * If a required field is missing, say so explicitly rather than guessing.
  * Prefer the shortest tool-call sequence that completes the job.
"""


def run(applicant_dir: Path) -> None:
    client = Anthropic()

    user_msg = (
        f"Underwrite the applicant in `{applicant_dir}`. "
        "Files: bank_statement.pdf, cibil.pdf, gst.json. "
        "Write intermediate parsed JSON into the same directory."
    )

    # NOTE: in a real deployment, discover tools via the MCP client
    # (`mcp.client.stdio`) and pass them as `tools=[…]` here.
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_msg}],
    )

    for block in resp.content:
        if block.type == "text":
            print(block.text)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the Unibac underwriting agent on one applicant.")
    ap.add_argument("applicant_dir", type=Path, help="Directory containing applicant files.")
    args = ap.parse_args()
    run(args.applicant_dir)


if __name__ == "__main__":
    main()
