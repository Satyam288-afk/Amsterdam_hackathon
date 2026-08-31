"""Reproducible synthetic evaluation for bounded reply diagnosis."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from services.recovery.diagnosis import diagnose_customer_reply_batch

_TEMPLATES = {
    "payment failure": [
        "The payment link fails with a bank technical error", "Our UPI payment did not go through", "The card was declined by the issuer", "The checkout page shows a failed transaction", "Bank gateway is timing out", "The payment link keeps showing an error", "Our finance team sees a transaction failure", "The bank rejected this payment attempt", "The payment page is not processing", "The transfer failed after confirmation",
    ],
    "approval delay": [
        "The finance approver has not signed off", "Waiting for CFO approval", "Our purchase head will approve next week", "Invoice is with the approver", "Finance needs internal sign off", "The director has not cleared the payment", "Approval is pending with accounts", "We need procurement approval first", "The authorized signatory is travelling", "The budget owner has not approved yet",
    ],
    "invoice dispute": [
        "The invoice amount is incorrect", "We dispute this charge", "The billed quantity does not match", "Please correct the wrong invoice", "We did not receive the services listed", "Tax calculation is mismatched", "This charge is not approved", "The invoice has duplicate line items", "We need a credit note before payment", "The purchase order amount differs",
    ],
    "payment delay": [
        "We will pay on Friday", "Cash flow is delayed until next week", "Payment will happen after month end", "Please give us three more days", "We will transfer it tomorrow", "Funds are expected this week", "Payment is delayed due to payroll", "We can pay after the weekend", "The payment run is scheduled next Monday", "We need a short extension",
    ],
    "promise missed": [
        "We promised last Friday but missed the payment", "Our earlier payment commitment was missed", "The promised transfer did not happen", "We failed to pay on the agreed date", "Last week's promise was not met", "We missed the commitment due to cash flow", "The scheduled payment was missed", "Sorry, we could not honor the promise", "Our previous promised date passed", "We missed the earlier Friday payment",
    ],
    "customer unreachable": [
        "The customer is not responding to calls", "No one answers the recovery number", "The contact has been unreachable", "We cannot reach their accounts team", "Calls go unanswered", "The customer has not replied", "Their phone is switched off", "No response after repeated follow ups", "The contact person is unavailable", "Messages remain unanswered",
    ],
}


def synthetic_corpus() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for cause, texts in _TEMPLATES.items():
        for text in texts:
            rows.append({"id": f"eval-{len(rows) + 1:03d}", "text": text, "expected_cause": cause})
    return rows


def run_diagnosis_evaluation() -> Dict[str, Any]:
    corpus = synthetic_corpus()
    diagnoses = diagnose_customer_reply_batch(corpus)
    rows = []
    confusion: Dict[str, Counter] = defaultdict(Counter)
    for item in corpus:
        diagnosis = diagnoses[item["id"]]
        predicted = diagnosis["cause"]
        confusion[item["expected_cause"]][predicted] += 1
        rows.append({**item, "predicted_cause": predicted, "confidence": diagnosis["confidence"], "source": diagnosis["source"], "correct": predicted == item["expected_cause"]})
    total = len(rows)
    correct = sum(row["correct"] for row in rows)
    sources = Counter(row["source"] for row in rows)
    per_class = {cause: {"total": len(texts), "correct": sum(row["correct"] for row in rows if row["expected_cause"] == cause), "accuracy": round(sum(row["correct"] for row in rows if row["expected_cause"] == cause) / len(texts) * 100, 1)} for cause, texts in _TEMPLATES.items()}
    return {"label": "Synthetic diagnosis evaluation", "disclaimer": "60 hand-authored fictional customer replies. This measures classification on a synthetic test set, not real merchant performance. Provider and fallback sources are reported separately.", "generated_at": datetime.now(timezone.utc).isoformat(), "total_cases": total, "correct": correct, "accuracy": round(correct / total * 100, 1), "fallback_count": sum(count for source, count in sources.items() if source != "gemini_structured_output"), "sources": dict(sources), "per_class": per_class, "confusion_matrix": {key: dict(value) for key, value in confusion.items()}, "rows": rows}


def load_evaluation(path: str) -> Dict[str, Any] | None:
    target = Path(path)
    return json.loads(target.read_text()) if target.exists() else None


def save_evaluation(path: str, result: Dict[str, Any]) -> None:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True); target.write_text(json.dumps(result, indent=2))
