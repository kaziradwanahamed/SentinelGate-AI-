"""Deterministic runaway-agent circuit breaker for the demo.

Simulates an agent iterating in a loop using mock execution only. The loop is
stopped the moment it would exceed either the configured iteration budget or the
configured token budget. No external systems are contacted.

The budgets come exclusively from server-side configuration
(:data:`MAX_AGENT_ITERATIONS`, :data:`MAX_TOKEN_BUDGET`). Client-supplied values
describe the simulated workload only and can never raise a budget.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.config import MAX_AGENT_ITERATIONS, MAX_TOKEN_BUDGET

# Upper bounds on the simulated workload a client may request, so a hostile or
# accidental value cannot make the demo loop do unbounded work before the budget
# check. The budget check would stop it anyway; this just caps the input range.
MAX_REQUESTED_ITERATIONS = 1000
MAX_TOKENS_PER_ITERATION = 100_000


def run_guarded_loop(
    requested_iterations: int,
    tokens_per_iteration: int,
    agent_id: str = "demo-agent",
) -> dict[str, Any]:
    """Run a mock agent loop under the server-side circuit breaker.

    Returns a result dict describing how far the loop got and whether the
    breaker tripped. ``status`` is ``"CIRCUIT_BREAKER_TRIGGERED"`` when a budget
    stopped the loop, otherwise ``"COMPLETED"``.
    """
    started = time.perf_counter()

    # Budgets are server-authoritative — taken from config, never from the caller.
    max_iterations = MAX_AGENT_ITERATIONS
    token_budget = MAX_TOKEN_BUDGET

    # Defensively clamp the client-supplied workload into a safe, non-negative
    # range. Pydantic also validates this at the API boundary; this guard keeps
    # the function safe when called directly (e.g. from tests or the MCP server).
    requested_iterations = max(0, min(int(requested_iterations), MAX_REQUESTED_ITERATIONS))
    tokens_per_iteration = max(0, min(int(tokens_per_iteration), MAX_TOKENS_PER_ITERATION))

    steps: list[dict[str, Any]] = []
    tokens_used = 0
    iterations_run = 0
    triggered = False
    trigger_reason: str | None = None

    for _ in range(requested_iterations):
        # Check both budgets BEFORE running the next iteration, so a blocked
        # iteration never executes and never consumes tokens.
        if iterations_run + 1 > max_iterations:
            triggered = True
            trigger_reason = "iteration_limit"
            break
        if tokens_used + tokens_per_iteration > token_budget:
            triggered = True
            trigger_reason = "token_budget"
            break

        # Mock execution only. No external side effects of any kind.
        iterations_run += 1
        tokens_used += tokens_per_iteration
        steps.append({
            "iteration": iterations_run,
            "tokens_used": tokens_used,
            "action": "simulated_agent_step",
            "status": "SIMULATED",
        })

    status = "CIRCUIT_BREAKER_TRIGGERED" if triggered else "COMPLETED"
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    return {
        "request_id": str(uuid4()),
        "agent_id": agent_id,
        "status": status,
        "stopped": triggered,
        "trigger_reason": trigger_reason,
        "iterations_run": iterations_run,
        "max_iterations": max_iterations,
        "tokens_used": tokens_used,
        "token_budget": token_budget,
        "requested_iterations": requested_iterations,
        "tokens_per_iteration": tokens_per_iteration,
        "steps": steps,
        # Gateway processing time only (this simulation), not a network round trip.
        "latency_ms": latency_ms,
        "latency_scope": "gateway_processing",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
