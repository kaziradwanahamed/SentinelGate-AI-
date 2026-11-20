from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from app.config import (
    ENABLE_HF_CLASSIFIER,
    PROMPT_GUARD_MODEL_ID,
    PROMPT_GUARD_THRESHOLD,
)

# These patterns are demo heuristics, not a complete prompt-injection detector.
INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"disregard (all )?(previous|prior|above) instructions",
    r"reveal (the )?(system prompt|secrets|credentials)",
    r"send (all )?(customer|user|private|confidential) (data|records|files)",
    r"exfiltrat(e|ion)",
    r"bypass (the )?(security|policy|safeguard|permission)",
    r"disable (the )?(security|guardrail|firewall)",
    r"you are now (in )?(developer|admin|system) mode",
]


@lru_cache(maxsize=1)
def _load_pipeline() -> Any:
    from transformers import pipeline

    # CPU mode is intentional for the first local MVP; production should benchmark
    # the selected model and runtime on the deployment hardware.
    return pipeline(
        "text-classification",
        model=PROMPT_GUARD_MODEL_ID,
        tokenizer=PROMPT_GUARD_MODEL_ID,
        device=-1,
        truncation=True,
        max_length=512,
    )


def classifier_mode() -> str:
    return "transformer" if ENABLE_HF_CLASSIFIER else "heuristic-demo"


def scan_text(text: str) -> dict[str, Any]:
    normalized = text or ""
    if ENABLE_HF_CLASSIFIER:
        try:
            prediction = _load_pipeline()(normalized[:8000])[0]
            label = str(prediction.get("label", "UNKNOWN")).upper()
            score = float(prediction.get("score", 0.0))
            malicious = label in {"INJECTION", "MALICIOUS", "JAILBREAK", "LABEL_1"} and score >= PROMPT_GUARD_THRESHOLD
            return {
                "mode": "transformer",
                "model_id": PROMPT_GUARD_MODEL_ID,
                "label": "MALICIOUS" if malicious else "BENIGN",
                "confidence": round(score, 4),
                "flagged": malicious,
                "note": "Model signal only; authorization is enforced separately.",
            }
        except Exception as exc:  # Keep the API usable if an optional model fails to load.
            fallback = _heuristic_scan(normalized)
            fallback["note"] = f"Transformer unavailable; heuristic fallback used ({type(exc).__name__})."
            return fallback
    return _heuristic_scan(normalized)


def _heuristic_scan(text: str) -> dict[str, Any]:
    lowered = text.lower()
    matches = [pattern for pattern in INJECTION_PATTERNS if re.search(pattern, lowered)]
    return {
        "mode": "heuristic-demo",
        "model_id": None,
        "label": "INJECTION_SIGNAL" if matches else "BENIGN",
        "confidence": 0.92 if matches else 0.65,
        "flagged": bool(matches),
        "matched_patterns": len(matches),
        "note": "Rule-based demo signal; not an SLM and not production-grade detection.",
    }
