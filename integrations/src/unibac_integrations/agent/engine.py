"""Streaming agent engine.

Thin event-emitting shim over the two existing agent backends (Anthropic
native tool-use, Ollama via its OpenAI-compatible `/v1`). The chat UI drives
one `AgentSession` per WebSocket; the session persists message history
between user turns.

Event types pushed to `emit` (async callback):
    text        {"type":"text","text":"..."}
    tool_call   {"type":"tool_call","id":"...","name":"...","input":{...}}
    tool_result {"type":"tool_result","id":"...","output":"...","is_error":bool}
    turn_end    {"type":"turn_end","stop_reason":"..."}
    error       {"type":"error","message":"..."}
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Awaitable, Callable, Literal

from .main import DISPATCH, SYSTEM_PROMPT, TOOLS

MAX_TURNS = 10
Emit = Callable[[dict], Awaitable[None]]
Backend = Literal["ollama", "anthropic"]


class AgentSession:
    """Multi-turn chat session. Each call to `send` processes one user turn
    (which may itself fan out into multiple model turns of tool_use → result)
    and emits events as they happen."""

    def __init__(self, backend: Backend = "ollama", max_turns: int = MAX_TURNS):
        self.backend: Backend = backend
        self.max_turns: int = max_turns
        self.messages: list[dict] = []  # provider-shaped message list

    async def send(self, user_text: str, emit: Emit) -> None:
        try:
            if self.backend == "anthropic":
                await self._run_anthropic(user_text, emit)
            else:
                await self._run_ollama(user_text, emit)
        except Exception as e:  # noqa: BLE001 — surface anything the UI can show
            await emit({"type": "error", "message": repr(e)})

    # ---- Anthropic -----------------------------------------------------------

    async def _run_anthropic(self, user_text: str, emit: Emit) -> None:
        from anthropic import Anthropic

        client = Anthropic()
        model = os.environ.get("LBI_AGENT_MODEL", "claude-opus-4-7")
        self.messages.append({"role": "user", "content": user_text})

        for _ in range(self.max_turns):
            resp = await asyncio.to_thread(
                client.messages.create,
                model=model,
                max_tokens=4096,
                system=[{"type": "text", "text": SYSTEM_PROMPT,
                         "cache_control": {"type": "ephemeral"}}],
                tools=TOOLS,
                messages=self.messages,
            )

            for block in resp.content:
                if block.type == "text" and block.text.strip():
                    await emit({"type": "text", "text": block.text})

            if resp.stop_reason != "tool_use":
                await emit({"type": "turn_end", "stop_reason": resp.stop_reason})
                self.messages.append({"role": "assistant", "content": resp.content})
                return

            tool_results: list[dict] = []
            for block in resp.content:
                if block.type == "tool_use":
                    await emit({"type": "tool_call", "id": block.id,
                                "name": block.name, "input": block.input})
                    out, is_err = await _dispatch(block.name, block.input)
                    await emit({"type": "tool_result", "id": block.id,
                                "output": out, "is_error": is_err})
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": out if isinstance(out, str) else json.dumps(out),
                        **({"is_error": True} if is_err else {}),
                    })

            self.messages.append({"role": "assistant", "content": resp.content})
            self.messages.append({"role": "user", "content": tool_results})

        await emit({"type": "error", "message": f"max_turns={self.max_turns}"})

    # ---- Ollama (OpenAI-compatible /v1) --------------------------------------

    async def _run_ollama(self, user_text: str, emit: Emit) -> None:
        from openai import OpenAI

        base_url = os.environ.get("LBI_OLLAMA_BASE", "http://localhost:11434/v1")
        model    = os.environ.get("LBI_AGENT_MODEL", "qwen3.6:35b-a3b")
        client   = OpenAI(base_url=base_url, api_key="ollama")

        if not self.messages:
            self.messages.append({"role": "system", "content": SYSTEM_PROMPT})
        self.messages.append({"role": "user", "content": user_text})

        tools = [{"type": "function",
                  "function": {"name": t["name"], "description": t["description"],
                               "parameters": t["input_schema"]}}
                 for t in TOOLS]

        for _ in range(self.max_turns):
            resp = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                messages=self.messages,
                tools=tools,
                tool_choice="auto",
            )
            msg = resp.choices[0].message

            if msg.content and msg.content.strip():
                await emit({"type": "text", "text": msg.content})

            if not msg.tool_calls:
                await emit({"type": "turn_end",
                            "stop_reason": resp.choices[0].finish_reason})
                self.messages.append({"role": "assistant",
                                      "content": msg.content or ""})
                return

            self.messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
            })

            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                await emit({"type": "tool_call", "id": tc.id,
                            "name": tc.function.name, "input": args})
                out, is_err = await _dispatch(tc.function.name, args)
                await emit({"type": "tool_result", "id": tc.id,
                            "output": out, "is_error": is_err})
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": out if isinstance(out, str) else json.dumps(out),
                })

        await emit({"type": "error", "message": f"max_turns={self.max_turns}"})


async def _dispatch(name: str, args: dict) -> tuple[Any, bool]:
    """Run a tool off-thread so the event loop stays responsive. The parsers
    hit disk and the Rust binary is a subprocess — neither is async-safe."""
    try:
        fn = DISPATCH[name]
    except KeyError:
        return (f"unknown tool: {name}", True)
    try:
        return (await asyncio.to_thread(fn, args), False)
    except Exception as e:  # noqa: BLE001 — same reason as above
        return (f"ERROR: {e!r}", True)
