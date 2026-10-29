"""Ollama backend for the LBI agent.

Talks to an Ollama server via its OpenAI-compatible `/v1` endpoint and
reuses the same tool DISPATCH map as the Anthropic backend. The tool schema
is translated from Anthropic's `input_schema` to OpenAI's `parameters` shape.

Useful for integration testing without burning API credits — correctness of
the model's judgement is not the point.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from openai import OpenAI

MAX_TURNS = 10


def _to_openai_tool(t: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        },
    }


def run(
    applicant_dir: Path,
    anthropic_tools: list[dict],
    dispatch: dict[str, Callable[[dict], Any]],
    system_prompt: str,
) -> None:
    base_url = os.environ.get("LBI_OLLAMA_BASE", "http://localhost:11434/v1")
    model    = os.environ.get("LBI_AGENT_MODEL", "qwen3.6:35b-a3b")
    client   = OpenAI(base_url=base_url, api_key="ollama")  # api_key value is ignored by ollama

    bank  = applicant_dir / "bank_statement.xlsx"
    cibil = applicant_dir / "cibil_report.pdf"
    gst   = applicant_dir / "gstr3b.xlsx"

    tools = [_to_openai_tool(t) for t in anthropic_tools]
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": (
            f"Underwrite the applicant in {applicant_dir.resolve()}.\n"
            f"Files: {bank.name}, {cibil.name}, {gst.name}."
        )},
    ]

    for turn in range(MAX_TURNS):
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        msg = resp.choices[0].message

        if msg.content and msg.content.strip():
            print(msg.content)

        if not msg.tool_calls:
            print(f"\n[turn {turn + 1}, finish_reason={resp.choices[0].finish_reason}]")
            return

        # Preserve the assistant message that carried the tool_calls.
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
        })

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            print(f"→ tool {name}({_short(args)})")
            try:
                out = dispatch[name](args)
                payload = json.dumps(out)
            except Exception as e:
                payload = f"ERROR: {e!r}"
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": payload,
            })

    print(f"\n[hit MAX_TURNS={MAX_TURNS}]")


def _short(d: dict) -> str:
    if "path" in d:
        return f"path={Path(d['path']).name}"
    return ",".join(d.keys())
