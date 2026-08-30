"""Bounded LLM-assisted diagnosis for recovery replies.

The model may classify text only. Recovery policy, outreach, payments, and
escalation remain deterministic in ``engine.py``.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from config import settings
from services.recovery.engine import classify_cause

ALLOWED_CAUSES = {
    "approval delay", "customer unreachable", "invoice dispute", "payment delay",
    "payment failure", "promise missed", "unknown",
}


def _validated(payload: Dict[str, Any], source: str, fallback: str) -> Dict[str, Any]:
    cause = str(payload.get("cause", "unknown")).strip().lower()
    if cause not in ALLOWED_CAUSES:
        cause = fallback if fallback in ALLOWED_CAUSES else "unknown"
    try:
        confidence = float(payload.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    reasoning = str(payload.get("reasoning", "No explanation supplied.")).strip()[:400]
    return {"cause": cause, "confidence": max(0.0, min(1.0, confidence)), "reasoning": reasoning, "source": source}


def diagnose_customer_reply(text: str, fallback_cause: str = "unknown") -> Dict[str, Any]:
    """Return a schema-validated diagnosis, with a deterministic offline fallback.

    External inference is opt-in because customer text can contain sensitive
    financial information. Set ENABLE_EXTERNAL_LLM_DIAGNOSIS=true and GROQ_API_KEY
    only after completing the appropriate data-processing review.
    """
    clean_text = text.strip()[:2000]
    if settings.external_llm_diagnosis_enabled and settings.groq_api_key:
        try:
            from groq import Groq
            completion = Groq(api_key=settings.groq_api_key).chat.completions.create(
                model=settings.llm_model_name,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "Classify a B2B payment-recovery customer reply. Return JSON only with cause (one of: approval delay, customer unreachable, invoice dispute, payment delay, payment failure, promise missed, unknown), confidence (0-1), and reasoning (max 25 words). Never recommend an action or invent facts."},
                    {"role": "user", "content": clean_text},
                ],
            )
            content = completion.choices[0].message.content or "{}"
            return _validated(json.loads(content), "groq_structured_output", fallback_cause)
        except Exception:
            # Model/API failures must never block a safe recovery workflow.
            pass
    result = classify_cause(clean_text, fallback_cause)
    return _validated({**result, "reasoning": "Keyword-based fallback used because external LLM diagnosis is not enabled or unavailable."}, result["source"], fallback_cause)
