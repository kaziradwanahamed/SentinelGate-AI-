from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import (
    APP_VERSION,
    CORS_ORIGINS,
    ENABLE_HF_CLASSIFIER,
    FRONTEND_DIST,
    MAX_AGENT_ITERATIONS,
    MAX_TOKEN_BUDGET,
)
from app.db import get_stats, init_db, list_events, save_event
from app.schemas import AnalyzeRequest, AnalyzeResponse, LoopSimRequest
from app.security.circuit_breaker import run_guarded_loop
from app.security.classifier import classifier_mode
from app.security.mock_tools import execute_mock_tool
from app.security.policy import evaluate_tool_call

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="SentinelGate AI API",
    description="Demo runtime security gateway for autonomous AI agent tool calls.",
    version=APP_VERSION,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "sentinelgate-api",
        "version": APP_VERSION,
        "classifier_mode": classifier_mode(),
        "transformer_enabled": ENABLE_HF_CLASSIFIER,
        "demo_only": True,
        "max_agent_iterations": MAX_AGENT_ITERATIONS,
        "max_token_budget": MAX_TOKEN_BUDGET,
    }


@app.get("/api/dashboard")
def dashboard() -> dict:
    return {
        "stats": get_stats(classifier_mode()),
        "events": list_events(10),
    }


@app.get("/api/events")
def events(limit: int = Query(default=20, ge=1, le=100)) -> dict:
    return {"events": list_events(limit)}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest) -> dict:
    # Measure real gateway processing latency with a monotonic high-resolution
    # timer: policy evaluation plus the mock-execution decision. This is
    # server-side processing time only and excludes the network round trip.
    started = time.perf_counter()
    result = evaluate_tool_call(payload)
    if result["decision"] == "ALLOW":
        execution = execute_mock_tool(payload.tool_name, payload.tool_arguments)
    else:
        execution = {
            "status": "NOT_EXECUTED",
            "message": "No tool was executed because the request was blocked or sent for review.",
        }
    gateway_latency_ms = round((time.perf_counter() - started) * 1000, 2)
    result["latency_ms"] = gateway_latency_ms

    classifier_label = str(result["classifier"].get("label", "UNKNOWN"))
    save_event({
        "id": result["request_id"],
        "created_at": result["created_at"],
        "agent_id": payload.agent_id,
        "tool_name": payload.tool_name,
        "decision": result["decision"],
        "risk_score": result["risk_score"],
        "summary": result["summary"],
        "provenance": payload.provenance,
        "classifier_label": classifier_label,
        "latency_ms": result["latency_ms"],
        "demo_case": payload.demo_case,
        "request_json": payload.model_dump(),
    })
    return {**result, "execution": execution, "latency_scope": "gateway_processing"}


@app.post("/api/simulate-loop")
def simulate_loop(payload: LoopSimRequest) -> dict:
    """Run a mock agent loop guarded by the server-side circuit breaker."""
    result = run_guarded_loop(
        payload.requested_iterations,
        payload.tokens_per_iteration,
        payload.agent_id,
    )
    decision = "BLOCK" if result["stopped"] else "ALLOW"
    risk_score = 100 if result["stopped"] else 5
    if result["stopped"]:
        summary = (
            f"Circuit breaker stopped a runaway agent loop "
            f"(reason: {result['trigger_reason']})."
        )
    else:
        summary = "Agent loop completed within the configured iteration and token budgets."

    save_event({
        "id": result["request_id"],
        "created_at": result["created_at"],
        "agent_id": payload.agent_id,
        "tool_name": "agent_loop",
        "decision": decision,
        "risk_score": risk_score,
        "summary": summary,
        "provenance": "trusted",
        "classifier_label": "NOT_SCANNED",
        "latency_ms": result["latency_ms"],
        "demo_case": payload.demo_case or "Runaway agent loop",
        "request_json": payload.model_dump(),
    })
    return {
        **result,
        "decision": decision,
        "risk_score": risk_score,
        "summary": summary,
        "execution": {"status": result["status"], "message": summary},
    }


# ---------------------------------------------------------------------------
# Static frontend (single-service deployment).
#
# When a built frontend exists (frontend/dist), FastAPI serves it from the same
# origin as the API, so the browser can use relative /api/* URLs. API routes,
# /docs, /openapi.json and /redoc are all registered above and therefore take
# precedence; the SPA fallback below only handles everything else. When no build
# is present (local dev with a separate Vite server), the original JSON root is
# kept so the existing dev workflow is unchanged.
# ---------------------------------------------------------------------------
_ASSETS_DIR = FRONTEND_DIST / "assets"
if _ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="assets")

_RESERVED_PREFIXES = ("api/", "docs", "redoc", "openapi.json")


@app.get("/", response_model=None)
def root() -> dict | FileResponse:
    index = FRONTEND_DIST / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {"name": "SentinelGate AI", "docs": "/docs", "health": "/api/health"}


@app.get("/{full_path:path}")
def spa_fallback(full_path: str) -> FileResponse:
    # Never shadow API or docs routes (they are matched before this catch-all,
    # but guard explicitly so unknown /api/* paths return JSON 404s, not HTML).
    if full_path.startswith(_RESERVED_PREFIXES):
        raise HTTPException(status_code=404, detail="Not found")
    candidate = FRONTEND_DIST / full_path
    if full_path and candidate.is_file():
        return FileResponse(candidate)
    index = FRONTEND_DIST / "index.html"
    if index.is_file():
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Frontend build not found")
