from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS security_events (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                decision TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                summary TEXT NOT NULL,
                provenance TEXT NOT NULL,
                classifier_label TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                demo_case TEXT,
                request_json TEXT NOT NULL,
                is_seed INTEGER NOT NULL DEFAULT 0
            )"""
        )
        count = conn.execute("SELECT COUNT(*) AS n FROM security_events").fetchone()["n"]
        if count == 0:
            _seed_demo_events(conn)


def _seed_demo_events(conn: sqlite3.Connection) -> None:
    now = datetime.now(timezone.utc)
    rows = [
        ("ALLOW", 4, "Invoice read permission verified", "trusted", "BENIGN", "Normal invoice read"),
        ("BLOCK", 94, "Untrusted prompt attempted to redirect customer data", "untrusted", "INJECTION_SIGNAL", "Indirect prompt injection"),
        ("BLOCK", 100, "Tool is not in the agent capability allowlist", "trusted", "NOT_SCANNED", "Unauthorized database delete"),
        ("REVIEW", 48, "Untrusted source used in a sensitive workflow", "unknown", "LOW_CONFIDENCE", "Unknown provenance"),
    ]
    for index, (decision, risk, summary, provenance, classifier, case) in enumerate(rows):
        event_id = str(uuid4())
        created = (now.replace(microsecond=0)).isoformat()
        request = {"tool_name": "read_file" if index == 0 else "send_email"}
        conn.execute(
            """INSERT INTO security_events
            (id, created_at, agent_id, tool_name, decision, risk_score, summary,
             provenance, classifier_label, latency_ms, demo_case, request_json, is_seed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (
                event_id, created, "demo-agent", request["tool_name"], decision,
                risk, summary, provenance, classifier, 3.4 + index, case,
                json.dumps(request),
            ),
        )


def save_event(event: dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO security_events
            (id, created_at, agent_id, tool_name, decision, risk_score, summary,
             provenance, classifier_label, latency_ms, demo_case, request_json, is_seed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (
                event["id"], event["created_at"], event["agent_id"], event["tool_name"],
                event["decision"], event["risk_score"], event["summary"],
                event["provenance"], event["classifier_label"], event["latency_ms"],
                event.get("demo_case"), json.dumps(event.get("request_json", {})),
            ),
        )


def list_events(limit: int = 20) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM security_events ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (max(1, min(limit, 100)),),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["request"] = json.loads(item.pop("request_json"))
        item["is_seed"] = bool(item["is_seed"])
        result.append(item)
    return result


def get_stats(classifier_mode: str) -> dict[str, Any]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT decision, COUNT(*) AS n FROM security_events GROUP BY decision"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) AS n FROM security_events").fetchone()["n"]
    counts = {row["decision"]: row["n"] for row in rows}
    blocked = counts.get("BLOCK", 0)
    return {
        "total_events": total,
        "allowed": counts.get("ALLOW", 0),
        "blocked": blocked,
        "review": counts.get("REVIEW", 0),
        "block_rate": round((blocked / total * 100) if total else 0, 1),
        "classifier_mode": classifier_mode,
    }
