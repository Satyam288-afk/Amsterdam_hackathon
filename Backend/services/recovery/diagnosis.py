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
    financial information. Set ENABLE_EXTERNAL_LLM_DIAGNOSIS=true and GOOGLE_API_KEY
    only after completing the appropriate data-processing review.
    """
    clean_text = text.strip()[:2000]
    if settings.external_llm_diagnosis_enabled and settings.google_api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.google_api_key)
            model = genai.GenerativeModel(
                settings.gemini_model_name,
                system_instruction="Classify a B2B payment-recovery customer reply. Return JSON only with cause (one of: approval delay, customer unreachable, invoice dispute, payment delay, payment failure, promise missed, unknown), confidence (0-1), and reasoning (max 25 words). Never recommend an action or invent facts.",
            )
            response = model.generate_content(clean_text, generation_config={"temperature": 0, "response_mime_type": "application/json"})
            return _validated(json.loads(getattr(response, "text", "{}")), "gemini_structured_output", fallback_cause)
        except Exception:
            # Model/API failures must never block a safe recovery workflow.
            pass
    result = classify_cause(clean_text, fallback_cause)
    return _validated({**result, "reasoning": "Keyword-based fallback used because external Gemini diagnosis is not enabled or unavailable."}, result["source"], fallback_cause)
