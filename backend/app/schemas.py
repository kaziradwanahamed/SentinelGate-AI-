from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    agent_id: str = Field(default="demo-agent", min_length=1, max_length=80)
    user_goal: str = Field(default="Review the invoice and summarize it.", max_length=4000)
    tool_name: str = Field(default="read_file", min_length=1, max_length=100)
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    provenance: Literal["trusted", "untrusted", "unknown"] = "trusted"
    retrieved_content: str = Field(default="", max_length=12000)
    demo_case: str | None = Field(default=None, max_length=80)


class CheckResult(BaseModel):
    name: str
    status: Literal["pass", "warn", "fail"]
    detail: str


class AnalyzeResponse(BaseModel):
    request_id: str
    decision: Literal["ALLOW", "BLOCK", "REVIEW"]
    risk_score: int
    summary: str
    reasons: list[str]
    checks: list[CheckResult]
    classifier: dict[str, Any]
    execution: dict[str, Any]
    latency_ms: float
    latency_scope: str = "gateway_processing"
    created_at: str


class LoopSimRequest(BaseModel):
    """Client-supplied description of a simulated agent loop.

    These values describe the workload only. The iteration and token budgets are
    enforced server-side and cannot be raised from here. Negative values are
    rejected by validation (``ge=0``), preventing a negative-limit bypass.
    """
    agent_id: str = Field(default="demo-agent", min_length=1, max_length=80)
    requested_iterations: int = Field(default=12, ge=0, le=1000)
    tokens_per_iteration: int = Field(default=400, ge=0, le=100000)
    demo_case: str | None = Field(default=None, max_length=80)


class DashboardStats(BaseModel):
    total_events: int
    allowed: int
    blocked: int
    review: int
    block_rate: float
    classifier_mode: str
