from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from pydantic import BaseModel

from agentse.config import get_settings
from agentse.graph import AgentRuntime
from agentse.memory.store import HierarchicalMemory
from agentse.tools.registry import default_registry

settings = get_settings()
app = FastAPI(title="Agentse", version="0.1.0")
_runtime: AgentRuntime | None = None


def runtime() -> AgentRuntime:
    global _runtime
    if _runtime is None:
        _runtime = AgentRuntime(settings)
    return _runtime


class ChatIn(BaseModel):
    task: str
    session_id: str | None = None


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (Path(__file__).with_name("index.html")).read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": settings.model}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/chat")
def chat(body: ChatIn) -> dict:
    if not body.task.strip():
        raise HTTPException(400, "empty task")
    result = runtime().invoke(body.task.strip(), session_id=body.session_id)
    return {
        "answer": result.get("final_answer"),
        "plan": result.get("plan"),
        "findings": result.get("findings"),
        "critique": result.get("critique"),
        "route": result.get("route_trace"),
        "scores": result.get("scores"),
        "session_id": result.get("session_id"),
    }


@app.get("/api/memory")
def memory(q: str = "") -> dict:
    mem = HierarchicalMemory(settings)
    hits = mem.search(q or "агент память архитектура", limit=8)
    return {"hits": [{"layer": h.layer, "text": h.text, "score": h.score, "meta": h.meta} for h in hits]}


@app.get("/api/tools")
def tools() -> dict:
    return {"tools": default_registry(settings).catalog()}


@app.get("/api/identity")
def identity() -> dict[str, str]:
    files = {}
    for name in ("SOUL.md", "IDENTITY.md", "AGENTS.md", "MEMORY.md"):
        path = settings.workspace / name
        files[name] = path.read_text(encoding="utf-8") if path.exists() else ""
    purpose = settings.workspace / "PURPOSE.md"
    files["PURPOSE.md"] = purpose.read_text(encoding="utf-8") if purpose.exists() else ""
    return files
