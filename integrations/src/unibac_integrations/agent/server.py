"""Agent chat WebSocket server.

    ws://localhost:8001/ws?backend=ollama   (default)
    ws://localhost:8001/ws?backend=anthropic

Client → server frames:
    {"type":"message","text":"..."}

Server → client frames: see engine.py event schema.
"""

from __future__ import annotations

import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .engine import AgentSession, Backend

app = FastAPI(title="LBI Agent Chat")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws")
async def ws(sock: WebSocket) -> None:
    await sock.accept()
    backend: Backend = "anthropic" if sock.query_params.get("backend") == "anthropic" else "ollama"
    session = AgentSession(backend=backend)
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
            await session.send(msg["text"], emit)
    except WebSocketDisconnect:
        return


def main() -> None:
    import uvicorn
    uvicorn.run("unibac_integrations.agent.server:app",
                host="0.0.0.0", port=8001, reload=False)


if __name__ == "__main__":
    main()
