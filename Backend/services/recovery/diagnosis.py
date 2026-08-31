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


def deterministic_reply_diagnosis(text: str, fallback_cause: str = "unknown") -> Dict[str, Any]:
    """Offline classifier used when a provider is disabled or a request fails.

    Keeping this separate avoids retrying an unavailable provider for every row
    in an evaluation batch.
    """
    result = classify_cause(text, fallback_cause)
    return _validated(
        {**result, "reasoning": "Keyword-based fallback used because external Gemini diagnosis is not enabled or unavailable."},
        result["source"],
        fallback_cause,
    )


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
    return deterministic_reply_diagnosis(clean_text, fallback_cause)


def diagnose_customer_reply_batch(items: list[Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
    """Classify evaluation replies in small batches to avoid rate-limit and truncation bias."""
    fallback = lambda batch: {item["id"]: deterministic_reply_diagnosis(item["text"], "unknown") for item in batch}
    if not (settings.external_llm_diagnosis_enabled and settings.google_api_key):
        return fallback(items)
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.google_api_key)
        model = genai.GenerativeModel(settings.gemini_model_name, system_instruction="Classify each B2B payment-recovery reply. Return JSON only: {items:[{id,cause,confidence,reasoning}]}. Cause must be one of approval delay, customer unreachable, invoice dispute, payment delay, payment failure, promise missed, unknown. Confidence must be a number from 0 to 1. Do not recommend actions or invent facts.")
        result: Dict[str, Dict[str, Any]] = {}
        for start in range(0, len(items), 10):
            batch = items[start:start + 10]
            try:
                prompt = "Replies to classify:\n" + "\n".join(f"{item['id']}: {item['text'][:500]}" for item in batch)
                response = model.generate_content(prompt, generation_config={"temperature": 0, "response_mime_type": "application/json"})
                parsed = json.loads(getattr(response, "text", "{}"))
                by_id = {str(row.get("id")): row for row in parsed.get("items", []) if isinstance(row, dict)}
                if len(by_id) != len(batch) or any(item["id"] not in by_id for item in batch):
                    result.update(fallback(batch))
                else:
                    result.update({item["id"]: _validated(by_id[item["id"]], "gemini_structured_output", "unknown") for item in batch})
            except Exception:
                result.update(fallback(batch))
        return result
    except Exception:
        return fallback(items)
