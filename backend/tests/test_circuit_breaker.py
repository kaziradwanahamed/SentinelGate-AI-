import pytest
from pydantic import ValidationError

from app.config import MAX_AGENT_ITERATIONS, MAX_TOKEN_BUDGET
from app.schemas import LoopSimRequest
from app.security.circuit_breaker import run_guarded_loop


def test_loop_stops_at_iteration_limit():
    # Request far more iterations than allowed, with cheap tokens so the
    # iteration budget is the binding limit.
    result = run_guarded_loop(requested_iterations=1000, tokens_per_iteration=1)
    assert result["status"] == "CIRCUIT_BREAKER_TRIGGERED"
    assert result["stopped"] is True
    assert result["trigger_reason"] == "iteration_limit"
    # Execution stops exactly at the budget: never more iterations than allowed.
    assert result["iterations_run"] == MAX_AGENT_ITERATIONS
    assert len(result["steps"]) == MAX_AGENT_ITERATIONS


def test_loop_stops_at_token_budget():
    # Spend the whole budget in a single iteration so the token budget trips
    # before the iteration limit.
    result = run_guarded_loop(requested_iterations=1000, tokens_per_iteration=MAX_TOKEN_BUDGET)
    assert result["status"] == "CIRCUIT_BREAKER_TRIGGERED"
    assert result["trigger_reason"] == "token_budget"
    assert result["tokens_used"] <= MAX_TOKEN_BUDGET


def test_loop_completes_within_budget():
    # A small workload that fits inside both budgets runs to completion.
    iters = max(1, MAX_AGENT_ITERATIONS - 1)
    result = run_guarded_loop(requested_iterations=iters, tokens_per_iteration=0)
    assert result["status"] == "COMPLETED"
    assert result["stopped"] is False
    assert result["trigger_reason"] is None
    assert result["iterations_run"] == iters


def test_client_cannot_exceed_server_budget():
    # Even a hostile, enormous request is capped by server-side budgets.
    result = run_guarded_loop(requested_iterations=10_000_000, tokens_per_iteration=1)
    assert result["iterations_run"] <= MAX_AGENT_ITERATIONS
    assert result["tokens_used"] <= MAX_TOKEN_BUDGET
    assert result["max_iterations"] == MAX_AGENT_ITERATIONS
    assert result["token_budget"] == MAX_TOKEN_BUDGET


def test_negative_limits_are_rejected():
    # Negative client-supplied values are rejected at the schema boundary.
    with pytest.raises(ValidationError):
        LoopSimRequest(requested_iterations=-5)
    with pytest.raises(ValidationError):
        LoopSimRequest(tokens_per_iteration=-100)


def test_negative_values_clamped_in_engine():
    # Defense in depth: even if a negative value reaches the engine directly,
    # it is clamped and never produces negative work.
    result = run_guarded_loop(requested_iterations=-5, tokens_per_iteration=-100)
    assert result["iterations_run"] == 0
    assert result["tokens_used"] == 0
    assert result["status"] == "COMPLETED"
