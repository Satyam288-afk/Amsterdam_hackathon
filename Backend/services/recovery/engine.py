"""Offline-capable B2B receivables recovery rules.

This module deliberately keeps financial decisions deterministic.  An LLM can
classify a customer reply or draft a message, but it cannot bypass these rules.
The in-memory store is a clearly labelled demo adapter; production deployments
can map the same fields to the existing Postgres/Supabase repository.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

MAX_AUTOMATED_ATTEMPTS = 3
MAX_VOICE_CALLS_PER_DAY = 1
HIGH_VALUE_INR = 200_000


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def money(value: int | float) -> int:
    return int(round(value))


def score_invoice(case: Dict[str, Any]) -> tuple[int, List[str]]:
    """Return a 0-100 risk score and explainable, field-derived reasons."""
    score = 0
    reasons: List[str] = []
    days_overdue = max(0, int(case.get("days_overdue", 0)))
    amount = money(case.get("amount", 0))
    attempts = max(0, int(case.get("attempts", 0)))

    overdue_points = min(30, round(days_overdue * 1.5))
    score += overdue_points
    if days_overdue:
        reasons.append(f"{days_overdue} days overdue")

    if amount >= 75_000:
        score += 29
        reasons.append("high outstanding amount")
    elif amount >= 40_000:
        score += 20
        reasons.append("material outstanding amount")
    elif amount >= 10_000:
        score += 10

    attempt_points = min(16, attempts * 8)
    score += attempt_points
    if attempts:
        reasons.append(f"{attempts} unsuccessful follow-up{'s' if attempts != 1 else ''}")

    if case.get("previous_promise_missed"):
        score += 15
        reasons.append("previous promise missed")
    if case.get("historical_payment_delay_days", 0) >= 15:
        score += 8
        reasons.append("historical payment delay")
    if case.get("responsiveness") == "low":
        score += 8
        reasons.append("low customer responsiveness")

    return min(100, score), reasons or ["recently overdue invoice"]


def classify_cause(text: str, fallback: str = "unknown") -> Dict[str, Any]:
    """Bounded fallback classifier.  Replaceable by existing LLM structured output."""
    normalized = text.lower()
    patterns = {
        "invoice dispute": ("dispute", "incorrect", "mismatch", "not received", "wrong invoice"),
        "approval delay": ("approval", "approver", "sign off", "finance head"),
        "payment failure": ("failed", "bank", "upi", "link", "technical"),
        "customer unreachable": ("unreachable", "no answer", "not responding"),
        "promise missed": ("missed", "promised", "last friday"),
        "payment delay": ("delay", "pay friday", "pay on", "cash flow", "next week"),
    }
    for cause, keywords in patterns.items():
        if any(keyword in normalized for keyword in keywords):
            return {"cause": cause, "confidence": 0.91, "source": "deterministic_reply_classifier"}
    return {"cause": fallback, "confidence": 0.5, "source": "fallback"}


def choose_action(case: Dict[str, Any], today: Optional[date] = None) -> Dict[str, str]:
    """Authoritative policy.  Never let a model choose outside this result."""
    today = today or date.today()
    status = case.get("status", "OPEN")
    if status == "RECOVERED":
        return {"action": "close", "channel": "none", "reason": "payment confirmed"}
    if status in {"STOPPED", "OPTED_OUT"}:
        return {"action": "stop", "channel": "none", "reason": "customer opted out"}
    if case.get("cause") == "invoice dispute":
        return {"action": "human_escalation", "channel": "manual", "reason": "invoice dispute requires human review"}

    promise_date = case.get("promise_to_pay_date")
    if promise_date and status == "PROMISE_TO_PAY":
        due = date.fromisoformat(promise_date)
        if due >= today:
            return {"action": "pause", "channel": "none", "reason": "valid promise-to-pay is active"}

    risk_score, _ = score_invoice(case)
    if case.get("failed_promise") or case.get("amount", 0) >= HIGH_VALUE_INR:
        return {"action": "human_escalation", "channel": "manual", "reason": "high value or failed promise"}
    if int(case.get("attempts", 0)) >= int(case.get("max_attempts", MAX_AUTOMATED_ATTEMPTS)):
        return {"action": "human_escalation", "channel": "manual", "reason": "maximum automated attempts reached"}
    if risk_score < 40:
        return {"action": "whatsapp_reminder", "channel": "whatsapp", "reason": "low-risk first reminder"}
    if risk_score <= 90 and case.get("whatsapp"):
        # WhatsApp is deliberately first for a responsive B2B contact. A voice
        # call remains the next approved action if this attempt does not resolve.
        return {"action": "whatsapp_payment_link", "channel": "whatsapp", "reason": "personalized payment-link outreach"}
    return {"action": "voice_call", "channel": "voice", "reason": "high-risk recovery outreach"}


def extract_promise_to_pay(text: str, amount: int, reference_date: Optional[date] = None) -> Dict[str, Any]:
    """Extract a bounded promise-to-pay signal from a customer statement."""
    normalized = text.lower()
    intent = any(token in normalized for token in ("pay", "payment", "denge", "kar denge", "karunga", "karungi"))
    if not intent:
        return {"promise_to_pay": False, "date": None, "amount": None}

    reference_date = reference_date or date.today()
    weekday_names = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
    target = None
    for name, weekday in weekday_names.items():
        if name in normalized:
            delta = (weekday - reference_date.weekday()) % 7
            target = reference_date + timedelta(days=delta or 7)
            break
    if "tomorrow" in normalized:
        target = reference_date + timedelta(days=1)
    return {"promise_to_pay": True, "date": target.isoformat() if target else None, "amount": amount}


def _event(title: str, notes: str, action: str = "system", channel: str = "system", outcome: str = "recorded") -> Dict[str, str]:
    return {"title": title, "notes": notes, "action": action, "channel": channel, "outcome": outcome, "timestamp": now_iso()}


def seeded_cases() -> List[Dict[str, Any]]:
    """Fictional data only. Open invoices total ₹18,40,000 at initial load."""
    source = [
        ("rec-001", "Aarav Mehta", "INV-2026-1042", 84_500, 18, "hi", 2, True, "approval delay", "medium", "OPEN"),
        ("rec-002", "Nila Textiles Pvt Ltd", "INV-2026-1043", 245_000, 31, "en", 3, True, "promise missed", "low", "ESCALATED"),
        ("rec-003", "Kaveri Logistics", "INV-2026-1044", 178_000, 12, "hi", 1, False, "payment delay", "medium", "PROMISE_TO_PAY"),
        ("rec-004", "BlueOrbit Solutions", "INV-2026-1045", 320_000, 22, "en", 1, False, "invoice dispute", "high", "OPEN"),
        ("rec-005", "MangoLeaf Retail", "INV-2026-1046", 96_000, 9, "ta", 0, False, "payment failure", "high", "OPEN"),
        ("rec-006", "Vardhan Components", "INV-2026-1047", 210_000, 40, "hi", 3, True, "customer unreachable", "low", "ESCALATED"),
        ("rec-007", "Northstar Consulting", "INV-2026-1048", 156_000, 15, "en", 1, False, "approval delay", "medium", "OPEN"),
        ("rec-008", "Sampoorna Foods", "INV-2026-1049", 285_000, 27, "hi", 2, False, "payment delay", "medium", "OPEN"),
        ("rec-009", "Delta Equipment", "INV-2026-1050", 265_500, 6, "en", 0, False, "unknown", "high", "OPEN"),
    ]
    cases: List[Dict[str, Any]] = []
    for index, (case_id, customer, invoice, amount, overdue, language, attempts, missed, cause, responsiveness, status) in enumerate(source):
        created = {
            "id": case_id,
            "customer_name": customer,
            "invoice_number": invoice,
            "amount": amount,
            "due_date": (date(2026, 8, 29) - timedelta(days=overdue)).isoformat(),
            "status": status,
            "days_overdue": overdue,
            "preferred_language": language,
            "phone": f"+91980000{100 + index}",
            "whatsapp": f"+91980000{100 + index}",
            "payment_link": f"https://rzp.io/i/demo-{invoice.lower()}",
            "attempts": attempts,
            "max_attempts": MAX_AUTOMATED_ATTEMPTS,
            "previous_promise_missed": missed,
            "historical_payment_delay_days": 0,
            "responsiveness": responsiveness,
            "cause": cause,
            "cause_confidence": 0.91 if cause != "unknown" else 0.5,
            "promise_to_pay_date": "2026-09-04" if case_id == "rec-003" else None,
            "promise_to_pay_amount": amount if case_id == "rec-003" else None,
            "failed_promise": status == "ESCALATED",
            "next_action_at": "2026-09-04T09:00:00+00:00" if case_id == "rec-003" else None,
            "recovered_amount": 0,
            "demo_data": True,
            "timeline": [_event("Risk detected", f"₹{amount:,} at risk", "risk_score", "system"), _event("Cause identified", cause.replace("_", " ").title(), "diagnosis", "system")],
        }
        score, reasons = score_invoice(created)
        created["risk_score"] = score
        created["risk_reasons"] = reasons
        policy = choose_action(created, today=date(2026, 8, 29))
        created["recommended_action"] = policy["action"]
        created["recommended_channel"] = policy["channel"]
        created["policy_reason"] = policy["reason"]
        if case_id == "rec-001":
            created["timeline"].extend([
                _event("WhatsApp reminder sent", "First reminder delivered with secure payment link", "whatsapp_payment_link", "whatsapp", "sent"),
                _event("Customer responded", "Approval is pending; customer asked for a Friday follow-up", "customer_reply", "whatsapp", "received"),
            ])
        if case_id == "rec-003":
            created["timeline"].append(_event("Promise to pay recorded", f"₹{amount:,} by Friday; automated outreach paused", "promise_to_pay", "voice", "recorded"))
        if status == "ESCALATED":
            created["timeline"].append(_event("Human escalation", "Automated outreach limit reached or promise failed", "human_escalation", "manual", "escalated"))
        cases.append(created)
    return cases


def calculate_benchmark(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Reproducible synthetic benchmark with explicitly encoded assumptions.

    Baseline assumes one generic reminder. Sambhaash assumes the bounded policy
    reaches a recoverable case when it is neither disputed nor unreachable.
    Amounts are calculated from the same seeded records, never hard-coded UI text.
    """
    evaluated = [c for c in cases if c.get("demo_data")]
    at_risk = sum(money(c["amount"]) for c in evaluated)
    baseline_recovered = 0
    sambhaash_recovered = 0
    baseline_contacts = len(evaluated)
    sambhaash_contacts = 0
    escalations = 0
    promises = 0
    for case in evaluated:
        cause = case.get("cause")
        amount = money(case["amount"])
        baseline_success = cause in {"payment delay", "payment failure"} and case.get("days_overdue", 0) < 15
        sambhaash_success = cause in {"payment delay", "payment failure", "approval delay"} and not case.get("failed_promise")
        if baseline_success:
            baseline_recovered += amount
        if sambhaash_success:
            sambhaash_recovered += amount
        sambhaash_contacts += min(case.get("attempts", 0) + 1, MAX_AUTOMATED_ATTEMPTS)
        if case.get("recommended_action") == "human_escalation":
            escalations += 1
        if case.get("promise_to_pay_date"):
            promises += 1
    return {
        "label": "Synthetic benchmark",
        "assumption_model": "Baseline sends one generic reminder. Sambhaash applies deterministic risk, diagnosis, approved intervention, and stop rules to fictional invoices.",
        "invoices_evaluated": len(evaluated),
        "amount_at_risk": at_risk,
        "baseline_recovered": baseline_recovered,
        "sambhaash_recovered": sambhaash_recovered,
        "baseline_recovery_rate": round(baseline_recovered / at_risk * 100, 1) if at_risk else 0,
        "recovery_rate": round(sambhaash_recovered / at_risk * 100, 1) if at_risk else 0,
        "improvement": money(sambhaash_recovered - baseline_recovered),
        "escalations": escalations,
        "promise_to_pay_count": promises,
        "average_contacts": round(sambhaash_contacts / len(evaluated), 1) if evaluated else 0,
        "net_recovered_value": money(sambhaash_recovered - (sambhaash_contacts * 12)),
    }


class RecoveryStore:
    """In-memory adapter for a no-credentials demo. State lives for app lifetime."""
    def __init__(self) -> None:
        self._cases = seeded_cases()

    def reset(self) -> Dict[str, Any]:
        """Restore the fictional dataset so the demo can always be replayed."""
        self._cases = seeded_cases()
        return self.summary()

    def list_cases(self) -> List[Dict[str, Any]]:
        return deepcopy(self._cases)

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        case = next((item for item in self._cases if item["id"] == case_id), None)
        return deepcopy(case) if case else None

    def _case(self, case_id: str) -> Dict[str, Any]:
        case = next((item for item in self._cases if item["id"] == case_id), None)
        if not case:
            raise KeyError(case_id)
        return case

    def _refresh_policy(self, case: Dict[str, Any]) -> None:
        score, reasons = score_invoice(case)
        case["risk_score"], case["risk_reasons"] = score, reasons
        policy = choose_action(case)
        case["recommended_action"] = policy["action"]
        case["recommended_channel"] = policy["channel"]
        case["policy_reason"] = policy["reason"]

    def execute_action(self, case_id: str) -> Dict[str, Any]:
        case = self._case(case_id)
        policy = choose_action(case)
        if policy["action"] in {"close", "stop", "pause", "human_escalation"}:
            if policy["action"] == "human_escalation":
                case["status"] = "ESCALATED"
                case["timeline"].append(_event("Human escalation", policy["reason"], "human_escalation", "manual", "escalated"))
            self._refresh_policy(case)
            return deepcopy(case)
        if policy["action"] == "voice_call":
            today_calls = sum(1 for event in case["timeline"] if event["action"] == "voice_call" and event["timestamp"][:10] == datetime.now(timezone.utc).date().isoformat())
            if today_calls >= MAX_VOICE_CALLS_PER_DAY:
                case["status"] = "ESCALATED"
                case["timeline"].append(_event("Human escalation", "Daily voice-call limit reached", "human_escalation", "manual", "escalated"))
                self._refresh_policy(case)
                return deepcopy(case)
        case["attempts"] += 1
        case["status"] = "IN_PROGRESS"
        title = "Voice recovery call initiated" if policy["channel"] == "voice" else "WhatsApp + payment link sent"
        notes = "Live channel optional; this demo records the approved recovery action."
        case["timeline"].append(_event(title, notes, policy["action"], policy["channel"], "sent"))
        self._refresh_policy(case)
        return deepcopy(case)

    def record_promise(self, case_id: str, customer_text: str, promise_date: Optional[str] = None) -> Dict[str, Any]:
        case = self._case(case_id)
        extracted = extract_promise_to_pay(customer_text, money(case["amount"]), date(2026, 8, 29))
        if not extracted["promise_to_pay"]:
            raise ValueError("No promise-to-pay signal found in customer response")
        final_date = promise_date or extracted["date"]
        if not final_date:
            raise ValueError("Promise date is required when it cannot be extracted")
        date.fromisoformat(final_date)
        case["promise_to_pay_date"] = final_date
        case["promise_to_pay_amount"] = extracted["amount"]
        case["next_action_at"] = f"{final_date}T09:00:00+00:00"
        case["status"] = "PROMISE_TO_PAY"
        case["timeline"].append(_event("Promise to pay recorded", f"₹{extracted['amount']:,} by {final_date}; automated outreach stopped", "promise_to_pay", "voice", "recorded"))
        case["timeline"].append(_event("Automated outreach stopped", "Valid promise-to-pay is active", "pause", "system", "stopped"))
        self._refresh_policy(case)
        return deepcopy(case)

    def confirm_payment(self, case_id: str) -> Dict[str, Any]:
        case = self._case(case_id)
        # Payment webhooks may be delivered more than once.  More importantly,
        # a completed demo case must remain a closed case with a clean audit log.
        if case["status"] == "RECOVERED":
            self._refresh_policy(case)
            return deepcopy(case)
        case["recovered_amount"] = money(case["amount"])
        case["status"] = "RECOVERED"
        case["next_action_at"] = None
        case["timeline"].append(_event("Payment confirmed", f"₹{case['recovered_amount']:,} recovered", "payment_confirmation", "payment_link", "recovered"))
        case["timeline"].append(_event("Case recovered", "No further outreach permitted", "close", "system", "closed"))
        self._refresh_policy(case)
        return deepcopy(case)

    def simulate_response(self, case_id: str, response_type: str) -> Dict[str, Any]:
        """Apply a labelled demo response through the same recovery state rules."""
        case = self._case(case_id)
        response_type = response_type.upper()
        if case.get("status") in {"RECOVERED", "STOPPED", "OPTED_OUT"}:
            self._refresh_policy(case)
            return deepcopy(case)
        if response_type == "PAYMENT_CONFIRMED":
            return self.confirm_payment(case_id)
        if response_type == "PROMISE_TO_PAY":
            return self.record_promise(case_id, "Friday ko payment kar denge.")
        if response_type == "DISPUTE":
            case["cause"] = "invoice dispute"
            case["cause_confidence"] = 0.91
            case["status"] = "ESCALATED"
            case["timeline"].append(_event("Invoice dispute detected", "Demo customer response requires human review", "diagnosis", "system", "received"))
            case["timeline"].append(_event("Human escalation", "Invoice dispute requires collections review", "human_escalation", "manual", "escalated"))
        elif response_type == "PAYMENT_FAILED":
            case["cause"] = "payment failure"
            case["cause_confidence"] = 0.91
            case["timeline"].append(_event("Payment failure reported", "Customer reported a payment issue; approved recovery policy recalculated", "customer_reply", "payment_link", "received"))
        elif response_type == "NO_RESPONSE":
            case["timeline"].append(_event("No customer response", "No reply was recorded; the next action remains policy controlled", "no_response", "system", "recorded"))
        else:
            raise ValueError("Unsupported demo response")
        self._refresh_policy(case)
        return deepcopy(case)

    def mark_failed_promises(self, as_of: date) -> int:
        count = 0
        for case in self._cases:
            promise = case.get("promise_to_pay_date")
            if case.get("status") == "PROMISE_TO_PAY" and promise and date.fromisoformat(promise) < as_of:
                case["failed_promise"] = True
                case["status"] = "ESCALATED"
                case["timeline"].append(_event("Promise missed", f"Payment not received by {promise}", "failed_promise", "system", "failed"))
                case["timeline"].append(_event("Human escalation", "Failed promise requires controlled escalation", "human_escalation", "manual", "escalated"))
                self._refresh_policy(case)
                count += 1
        return count

    def summary(self) -> Dict[str, Any]:
        cases = self._cases
        open_cases = [c for c in cases if c["status"] not in {"RECOVERED", "STOPPED", "OPTED_OUT"}]
        at_risk = sum(money(c["amount"]) - money(c.get("recovered_amount", 0)) for c in open_cases)
        recovered = sum(money(c.get("recovered_amount", 0)) for c in cases)
        initial_total = at_risk + recovered
        return {
            "demo_data": True,
            "revenue_at_risk": at_risk,
            "recovered_revenue": recovered,
            "recovery_rate": round(recovered / initial_total * 100, 1) if initial_total else 0,
            "open_recovery_cases": len(open_cases),
            "overdue_invoices": len(open_cases),
            "promise_to_pay": sum(1 for c in cases if c["status"] == "PROMISE_TO_PAY"),
            "escalations": sum(1 for c in cases if c["status"] == "ESCALATED"),
        }
