from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.schemas import AnalyzeRequest
from app.security.classifier import scan_text

HARD_BLOCK_TOOLS = {
    "delete_database",
    "execute_shell",
    "transfer_funds",
    "export_customer_data",
    "disable_security",
}
SENSITIVE_TERMS = re.compile(
    r"customer[_ -]?data|user[_ -]?records|credentials|passwords?|secret[_ -]?key|payroll|ssn|national[_ -]?id",
    re.IGNORECASE,
)
HIGH_IMPACT_TOOLS = {"send_email", "write_file", "execute_code", "update_record", "create_payment"}
AGENT_CAPABILITIES = {
    "finance-assistant-01": {"read_file", "search_documents", "send_email"},
    "research-assistant-02": {"read_file", "search_documents"},
    "claude-mcp-demo": {"read_file", "search_documents", "send_email"},
    "demo-agent": {"read_file", "search_documents", "send_email"},
}


def evaluate_tool_call(payload: AnalyzeRequest) -> dict[str, Any]:
    started = time.perf_counter()
    checks: list[dict[str, str]] = []
    reasons: list[str] = []
    risk = 0
    requires_review = False

    # Capabilities are looked up server-side; clients cannot grant themselves tools.
    permitted_tools = AGENT_CAPABILITIES.get(payload.agent_id, {"read_file"})
    allowed = payload.tool_name in permitted_tools
    checks.append({
        "name": "Capability policy",
        "status": "pass" if allowed else "fail",
        "detail": (
            f"{payload.tool_name} is in the agent capability allowlist."
            if allowed else f"{payload.tool_name} is not in the agent capability allowlist."
        ),
    })
    if not allowed:
        risk += 100
        reasons.append("Tool is not authorized for this agent.")

    if payload.tool_name in HARD_BLOCK_TOOLS:
        risk = 100
        reasons.append("The requested tool is classified as a prohibited high-impact action in this demo policy.")
        checks.append({"name": "High-impact action guard", "status": "fail", "detail": "This tool is deny-listed by the demo policy."})
    else:
        checks.append({"name": "High-impact action guard", "status": "pass", "detail": "No prohibited tool name was requested."})

    context_text = "\n".join([
        payload.user_goal,
        payload.retrieved_content,
        payload.tool_name,
        str(payload.tool_arguments),
    ])
    classifier = scan_text(context_text)
    if classifier["flagged"]:
        risk += 65
        reasons.append("Prompt-injection or instruction-override signal detected in the request context.")
        checks.append({"name": "Context security scan", "status": "fail", "detail": "Suspicious instruction pattern detected."})
    else:
        checks.append({"name": "Context security scan", "status": "pass", "detail": "No known injection pattern was detected by the active scanner."})

    sensitive_blob = str(payload.tool_arguments)
    has_sensitive = bool(SENSITIVE_TERMS.search(sensitive_blob))
    external_target = any(
        key.lower() in {"to", "recipient", "email"}
        and isinstance(value, str)
        and not value.lower().endswith(("@acme.example", "@example.com"))
        for key, value in payload.tool_arguments.items()
    )
    if has_sensitive and external_target:
        risk += 55
        reasons.append("Sensitive-data indicator is paired with an external recipient.")
        checks.append({"name": "Data exfiltration guard", "status": "fail", "detail": "Sensitive data and an external destination appear in the same tool arguments."})
    elif has_sensitive:
        risk += 25
        reasons.append("Sensitive-data indicator found in tool arguments; review is required.")
        checks.append({"name": "Data exfiltration guard", "status": "warn", "detail": "Sensitive-data terms require contextual review."})
    else:
        checks.append({"name": "Data exfiltration guard", "status": "pass", "detail": "No sensitive-data marker was found in the supplied arguments."})

    if payload.provenance == "untrusted":
        risk += 35 if (classifier["flagged"] or payload.tool_name in HIGH_IMPACT_TOOLS) else 15
        requires_review = True
        checks.append({"name": "Data provenance", "status": "warn", "detail": "The request depends on untrusted external content."})
        if classifier["flagged"] or payload.tool_name in HIGH_IMPACT_TOOLS:
            reasons.append("Untrusted content is influencing a sensitive or suspicious tool action.")
    elif payload.provenance == "unknown":
        risk += 15
        requires_review = True
        checks.append({"name": "Data provenance", "status": "warn", "detail": "The source trust level is unknown."})
        reasons.append("Data provenance is unknown; human review is recommended.")
    else:
        checks.append({"name": "Data provenance", "status": "pass", "detail": "The supplied source is marked trusted by this demo request."})

    if payload.tool_name in HIGH_IMPACT_TOOLS and risk >= 20:
        checks.append({"name": "Human approval", "status": "warn", "detail": "Sensitive workflow requires human approval when risk signals are present."})
        reasons.append("Sensitive action requires human approval due to risk signals.")

    risk = min(100, risk)
    if payload.tool_name in HARD_BLOCK_TOOLS or not allowed or (classifier["flagged"] and payload.provenance == "untrusted") or (has_sensitive and external_target):
        decision = "BLOCK"
    elif risk >= 25 or requires_review:
        decision = "REVIEW"
    else:
        decision = "ALLOW"

    if not reasons:
        reasons.append("The requested action passed the configured demo checks.")
    summary = {
        "ALLOW": "Request passed the demo policy checks.",
        "BLOCK": "Request was blocked before the simulated tool could run.",
        "REVIEW": "Request requires human review before execution.",
    }[decision]
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    return {
        "request_id": str(uuid4()),
        "decision": decision,
        "risk_score": risk,
        "summary": summary,
        "reasons": list(dict.fromkeys(reasons)),
        "checks": checks,
        "classifier": classifier,
        "latency_ms": latency_ms,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
