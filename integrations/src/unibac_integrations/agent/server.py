"""Agent chat WebSocket server.

    ws://localhost:8001/ws?backend=ollama   (default)
    ws://localhost:8001/ws?backend=anthropic&token=<LBI_AGENT_TOKEN>

Guardrails (frontier models burn real money, so defence in depth):
  * Binds 127.0.0.1 only — not reachable off-host.
  * Frontier (Anthropic) backend requires `LBI_AGENT_ALLOW_FRONTIER=1`
    AND a shared token matching `LBI_AGENT_TOKEN`. If the token env var
    is empty the frontier backend is unavailable even locally.
  * Per-session: ≤ MAX_MESSAGES user turns, ≤ MAX_MSG_CHARS per message,
    ≥ MIN_INTERVAL_S between messages, and MAX_TURNS tool-use loops per
    turn (lower when frontier is selected).

Client → server frames:
    {"type":"message","text":"..."}

Server → client frames: see engine.py event schema.
"""

from __future__ import annotations

import json
import os
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from .engine import AgentSession, Backend

MAX_MESSAGES    = 20
MAX_MSG_CHARS   = 4_000
MIN_INTERVAL_S  = 2.0

app = FastAPI(title="LBI Agent Chat")
app.add_middleware(
    CORSMiddleware,
    # Only the two local dev UI origins can connect — the WS handshake also
    # checks Origin against this list.
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def health() -> dict:
    return {"status": "ok"}


def _frontier_allowed(token: str | None) -> tuple[bool, str]:
    if os.environ.get("LBI_AGENT_ALLOW_FRONTIER") != "1":
        return False, "frontier backend disabled (set LBI_AGENT_ALLOW_FRONTIER=1 to enable)"
    expected = os.environ.get("LBI_AGENT_TOKEN")
    if not expected:
        return False, "frontier backend requires LBI_AGENT_TOKEN to be set on the server"
    if token != expected:
        return False, "invalid token for frontier backend"
    return True, ""


@app.websocket("/ws")
async def ws(sock: WebSocket) -> None:
    requested = sock.query_params.get("backend", "ollama")
    token     = sock.query_params.get("token")

    if requested == "anthropic":
        ok, reason = _frontier_allowed(token)
        if not ok:
            await sock.close(code=status.WS_1008_POLICY_VIOLATION, reason=reason)
            return
        backend: Backend = "anthropic"
        max_turns = 6
    else:
        backend = "ollama"
        max_turns = 10

    await sock.accept()
    session = AgentSession(backend=backend, max_turns=max_turns)
    msg_count = 0
    last_at   = 0.0
    await sock.send_json({"type": "ready", "backend": backend})

    async def emit(ev: dict) -> None:
        await sock.send_text(json.dumps(ev, default=str))

    try:
        while True:
            raw = await sock.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await emit({"type": "error", "message": "invalid json"})
                continue
            if msg.get("type") != "message" or not isinstance(msg.get("text"), str):
                await emit({"type": "error", "message": "expected {type:'message',text:str}"})
                continue

            text = msg["text"]
            if len(text) > MAX_MSG_CHARS:
                await emit({"type": "error",
                            "message": f"message too long (> {MAX_MSG_CHARS} chars)"})
                continue
            msg_count += 1
            if msg_count > MAX_MESSAGES:
                await emit({"type": "error",
                            "message": f"session message cap reached ({MAX_MESSAGES})"})
                await sock.close(code=status.WS_1008_POLICY_VIOLATION,
                                 reason="session cap")
                return
            now = time.monotonic()
            if now - last_at < MIN_INTERVAL_S:
                await emit({"type": "error",
                            "message": f"rate limited: ≥ {MIN_INTERVAL_S}s between messages"})
                continue
            last_at = now

            await session.send(text, emit)
    except WebSocketDisconnect:
        return


def main() -> None:
    import uvicorn
    uvicorn.run("unibac_integrations.agent.server:app",
                host="127.0.0.1", port=8001, reload=False)


if __name__ == "__main__":
    main()
