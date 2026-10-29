"""LBI underwriting agent.

Drives the Python parsers + Rust `lbi-core cam` as native Anthropic tools so
Claude can underwrite one applicant end-to-end:

    1. parse_bank_statement / parse_cibil / parse_gst
    2. build_cam
    3. Summarise decision + rationale.

The system prompt + tool list are marked `cache_control: ephemeral` because
they change rarely.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from anthropic import Anthropic

from unibac_integrations.parsers import (
    BankStatementParser,
    CibilParser,
    GstParser,
)

MODEL     = os.environ.get("LBI_AGENT_MODEL", "claude-opus-4-7")
CORE_BIN  = os.environ.get("LBI_CORE_BINARY", "lbi-core")
MAX_TURNS = 10

SYSTEM_PROMPT = """\
You are the Unibac underwriting agent for a vehicle-finance NBFC.

For each applicant you are given a directory containing three raw files:
    bank_statement.xlsx, cibil_report.pdf, gstr3b.xlsx

Your job:
  1. Call parse_bank_statement, parse_cibil and parse_gst on those files
     (in any order; you can call them in parallel if that helps).
  2. Call build_cam with the three parsed-JSON blobs you received.
  3. Reply with a short readout: decision (APPROVE / REFER / DECLINE), the
     top three rationale points, and any missing data that forced a REFER.

Rules:
  * Never fabricate numbers that the tools did not return.
  * If a required field is missing, say so explicitly rather than guessing.
  * Prefer the shortest tool-call sequence that completes the job.
"""

TOOLS = [
    {
        "name": "parse_bank_statement",
        "description": "Parse an Indian bank account statement (.xlsx) into a canonical summary JSON.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "parse_cibil",
        "description": "Parse a CIBIL TransUnion credit report (.pdf) into a canonical summary JSON.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "parse_gst",
        "description": "Parse a GSTR-3B workbook (.xlsx) into a canonical summary JSON.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "build_cam",
        "description": (
            "Combine parsed bank, CIBIL and GST JSONs into a Credit Appraisal Memo "
            "with a decision (APPROVE / REFER / DECLINE) and rationale."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "bank":  {"type": "object", "description": "Bank summary JSON from parse_bank_statement."},
                "cibil": {"type": "object", "description": "CIBIL summary JSON from parse_cibil."},
                "gst":   {"type": "object", "description": "GST summary JSON from parse_gst."},
            },
            "required": ["bank", "cibil", "gst"],
        },
    },
]


# ---- Tool implementations -----------------------------------------------------


def _tool_parse_bank(path: str) -> dict:
    return BankStatementParser().parse(Path(path)).model_dump(mode="json")


def _tool_parse_cibil(path: str) -> dict:
    return CibilParser().parse(Path(path)).model_dump(mode="json")


def _tool_parse_gst(path: str) -> dict:
    return GstParser().parse(Path(path)).model_dump(mode="json")


def _tool_build_cam(bank: dict, cibil: dict, gst: dict) -> dict:
    with tempfile.TemporaryDirectory() as td:
        bank_p  = Path(td) / "bank.json"
        cibil_p = Path(td) / "cibil.json"
        gst_p   = Path(td) / "gst.json"
        out_p   = Path(td) / "cam.json"
        bank_p.write_text(json.dumps(bank))
        cibil_p.write_text(json.dumps(cibil))
        gst_p.write_text(json.dumps(gst))
        subprocess.run(
            [CORE_BIN, "cam",
             "--bank",  str(bank_p),
             "--cibil", str(cibil_p),
             "--gst",   str(gst_p),
             "--out",   str(out_p)],
            check=True,
        )
        return json.loads(out_p.read_text())


DISPATCH = {
    "parse_bank_statement": lambda i: _tool_parse_bank(i["path"]),
    "parse_cibil":          lambda i: _tool_parse_cibil(i["path"]),
    "parse_gst":            lambda i: _tool_parse_gst(i["path"]),
    "build_cam":            lambda i: _tool_build_cam(i["bank"], i["cibil"], i["gst"]),
}


# ---- Agent loop ---------------------------------------------------------------


def run(applicant_dir: Path) -> None:
    backend = os.environ.get("LBI_AGENT_BACKEND", "anthropic").lower()
    if backend == "ollama":
        from .ollama_backend import run as ollama_run
        ollama_run(applicant_dir, TOOLS, DISPATCH, SYSTEM_PROMPT)
        return
    _run_anthropic(applicant_dir)


def _run_anthropic(applicant_dir: Path) -> None:
    client = Anthropic()
    bank = applicant_dir / "bank_statement.xlsx"
    cibil = applicant_dir / "cibil_report.pdf"
    gst  = applicant_dir / "gstr3b.xlsx"

    user_msg = (
        f"Underwrite the applicant in {applicant_dir.resolve()}.\n"
        f"Files: {bank.name}, {cibil.name}, {gst.name}."
    )

    messages: list = [{"role": "user", "content": user_msg}]

    for turn in range(MAX_TURNS):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            tools=TOOLS,
            messages=messages,
        )

        # Print any text the model produced this turn.
        for block in resp.content:
            if block.type == "text" and block.text.strip():
                print(block.text)

        if resp.stop_reason != "tool_use":
            print(f"\n[turn {turn + 1}, stop_reason={resp.stop_reason}]")
            return

        # Execute tool_use blocks and append tool_result blocks for the next turn.
        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                print(f"→ tool {block.name}({_short(block.input)})")
                try:
                    out = DISPATCH[block.name](block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(out),
                    })
                except Exception as e:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"ERROR: {e!r}",
                        "is_error": True,
                    })

        messages.append({"role": "assistant", "content": resp.content})
        messages.append({"role": "user",      "content": tool_results})

    print(f"\n[hit MAX_TURNS={MAX_TURNS}]")


def _short(d: dict) -> str:
    if "path" in d:
        return f"path={Path(d['path']).name}"
    return ",".join(d.keys())


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the Unibac underwriting agent on one applicant.")
    ap.add_argument("applicant_dir", type=Path, help="Directory containing applicant files.")
    args = ap.parse_args()
    run(args.applicant_dir)


if __name__ == "__main__":
    main()
