"""API FastAPI: ligações por voz, ocorrências e painel ao vivo."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import agent, report, severity, storage
from .config import settings
from .schemas import CallStartRequest, TurnRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("voz")

app = FastAPI(title=settings.app_name)

_clients: Set[WebSocket] = set()


async def _broadcast(event: dict) -> None:
    dead = []
    for ws in list(_clients):
        try:
            await ws.send_text(json.dumps(event, ensure_ascii=False))
        except Exception:  # noqa: BLE001
            dead.append(ws)
    for ws in dead:
        _clients.discard(ws)


@app.on_event("startup")
def _startup() -> None:
    storage.init_db()
    log.info("DB inicializado em %s", settings.db_path)


# --- API ----------------------------------------------------------------------
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name,
            "llm": bool(settings.llm_enabled and settings.llm_api_key)}


@app.post("/api/call/start")
async def call_start(req: CallStartRequest) -> dict:
    resp = agent.start_call(req)
    await _broadcast({"type": "occurrence_new", "occurrence": resp.occurrence.model_dump()})
    return resp.model_dump()


@app.post("/api/call/turn")
async def call_turn(req: TurnRequest) -> dict:
    resp = await agent.process_turn(req)
    await _broadcast({"type": "occurrence_update", "occurrence": resp.occurrence.model_dump(),
                      "state": resp.state.value})
    return resp.model_dump()


@app.get("/api/occurrences")
def occurrences(limit: int = 50) -> list:
    return [o.model_dump() for o in storage.list_occurrences(limit)]


@app.get("/api/occurrences/{call_id}")
def occurrence(call_id: str):
    occ = storage.get_occurrence(call_id)
    if not occ:
        return JSONResponse({"error": "não encontrada"}, status_code=404)
    return occ.model_dump()


@app.get("/api/occurrences/{call_id}/relatorio")
def occurrence_report(call_id: str):
    rep = report.build_report(call_id)
    if not rep:
        return JSONResponse({"error": "não encontrada"}, status_code=404)
    return rep


@app.get("/api/gravidade")
def gravidade() -> dict:
    return {"matriz": severity.matrix_summary()}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    _clients.add(ws)
    try:
        await ws.send_text(json.dumps(
            {"type": "occurrences", "data": [o.model_dump() for o in storage.list_occurrences(50)]},
            ensure_ascii=False))
        while True:
            await asyncio.sleep(30)
            await ws.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(ws)


# --- Frontend estático --------------------------------------------------------
_STATIC = __import__("os").path.join(__import__("os").path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_STATIC), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(f"{_STATIC}/index.html")


@app.get("/dashboard")
def dashboard() -> FileResponse:
    return FileResponse(f"{_STATIC}/dashboard.html")
