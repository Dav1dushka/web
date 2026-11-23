from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .core import analyze_log
from .database import get_analysis, get_history, init_db, save_analysis

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="SOC Triage Desk",
    version="1.0.0",
    description="A local defensive log-analysis and incident-triage learning platform.",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


class AnalyzeRequest(BaseModel):
    source_name: str = Field(default="Pasted authentication log", min_length=1, max_length=120)
    log_text: str = Field(min_length=1, max_length=1_000_000)


@app.get("/", include_in_schema=False)
async def dashboard():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "soc-triage-desk"}


@app.get("/api/rules")
async def rules():
    return [
        {"id": "AUTH-001", "name": "Repeated failed authentication", "severity": "HIGH", "threshold": "5 or more failed events from one IP"},
        {"id": "AUTH-002", "name": "Possible password spraying", "severity": "HIGH", "threshold": "5 or more failed events across 3 or more usernames"},
        {"id": "AUTH-003", "name": "Repeated invalid-user probes", "severity": "MEDIUM", "threshold": "3 or more invalid-user events from one IP"},
        {"id": "AUTH-004", "name": "Successful login after failed attempts", "severity": "CRITICAL", "threshold": "A success follows one or more failures from the same IP in the supplied log"},
        {"id": "PRIV-001", "name": "Privileged command executed", "severity": "MEDIUM", "threshold": "A sudo command event is present"},
    ]


@app.post("/api/analyze", status_code=201)
async def analyze(payload: AnalyzeRequest):
    try:
        result = analyze_log(payload.log_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    analysis_id = save_analysis(payload.source_name, result)
    return {"id": analysis_id, "source_name": payload.source_name, **result}


@app.get("/api/history")
async def history(limit: int = 20):
    return get_history(limit)


@app.get("/api/history/{analysis_id}")
async def analysis_detail(analysis_id: int):
    item = get_analysis(analysis_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return item
