from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_positive_int(name: str, default: int) -> int:
    """Read a positive integer from the environment.

    Falls back to the (positive) default if the value is missing, non-numeric,
    zero, or negative. This keeps the circuit-breaker budgets server-authoritative
    and prevents a misconfigured or hostile value from disabling the limit.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw.strip())
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


CORS_ORIGINS = [
    item.strip()
    for item in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if item.strip()
]
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "data/sentinelgate.db"))
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = BACKEND_DIR / DATABASE_PATH

# Built React frontend to serve for the single-service (combined) deployment.
# Overridable via FRONTEND_DIST; defaults to ../frontend/dist relative to backend.
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", str(BACKEND_DIR.parent / "frontend" / "dist")))

ENABLE_HF_CLASSIFIER = env_bool("ENABLE_HF_CLASSIFIER", False)
PROMPT_GUARD_MODEL_ID = os.getenv(
    "PROMPT_GUARD_MODEL_ID", "protectai/deberta-v3-base-prompt-injection-v2"
)
PROMPT_GUARD_THRESHOLD = float(os.getenv("PROMPT_GUARD_THRESHOLD", "0.80"))

# Runaway-agent circuit breaker budgets. These are enforced server-side and are
# never overridable by client-supplied request values.
MAX_AGENT_ITERATIONS = env_positive_int("MAX_AGENT_ITERATIONS", 5)
MAX_TOKEN_BUDGET = env_positive_int("MAX_TOKEN_BUDGET", 2000)

APP_VERSION = "0.1.0"
