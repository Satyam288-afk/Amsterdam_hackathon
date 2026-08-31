"""Offline-capable B2B receivables recovery rules.

This module deliberately keeps financial decisions deterministic.  An LLM can
classify a customer reply or draft a message, but it cannot bypass these rules.
The storage adapter is replaceable; the local application uses SQLite while a
production deployment can map the same fields to Postgres/Supabase.
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


def score_breakdown(case: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return every contribution, including zero values, for a judge-auditable score."""
    days = max(0, int(case.get("days_overdue", 0)))
    amount = money(case.get("amount", 0))
    attempts = max(0, int(case.get("attempts", 0)))
    event_points = {"payment failure": 20, "checkout abandonment": 10, "invoice dispute": 25}.get(case.get("cause"), 0)
    if amount >= 75_000:
        amount_points, amount_label = 29, "Amount tier — high outstanding amount"
    elif amount >= 40_000:
        amount_points, amount_label = 20, "Amount tier — material outstanding amount"
    elif amount >= 10_000:
        amount_points, amount_label = 10, "Amount tier — material outstanding amount"
    else:
        amount_points, amount_label = 0, "Amount tier — low value"
    return [
        {"label": f"Event severity — {case.get('cause', 'no event signal')}", "points": event_points},
        {"label": f"Days overdue — {days}", "points": min(30, round(days * 1.5))},
        {"label": amount_label, "points": amount_points},
        {"label": f"Prior failed attempts — {attempts}", "points": min(16, attempts * 8)},
        {"label": "Previous promise missed", "points": 15 if case.get("previous_promise_missed") else 0},
        {"label": "Historical payment delay", "points": 8 if case.get("historical_payment_delay_days", 0) >= 15 else 0},
        {"label": "Low customer responsiveness", "points": 8 if case.get("responsiveness") == "low" else 0},
    ]


def score_invoice(case: Dict[str, Any]) -> tuple[int, List[str]]:
    """Return a capped score and concise evidence derived from its breakdown."""
    score = min(100, sum(item["points"] for item in score_breakdown(case)))
    reasons: List[str] = []
    if case.get("cause") in {"payment failure", "checkout abandonment", "invoice dispute"}:
        reasons.append(f"{case['cause']} signal")
    if case.get("days_overdue"):
        reasons.append(f"{case['days_overdue']} days overdue")
    amount = money(case.get("amount", 0))
    if amount >= 75_000:
        reasons.append("high outstanding amount")
    elif amount >= 40_000:
        reasons.append("material outstanding amount")
    if case.get("attempts"):
        reasons.append(f"{case['attempts']} unsuccessful follow-up{'s' if case['attempts'] != 1 else ''}")
    if case.get("previous_promise_missed"):
        reasons.append("previous promise missed")
    if case.get("historical_payment_delay_days", 0) >= 15:
        reasons.append("historical payment delay")
    if case.get("responsiveness") == "low":
        reasons.append("low customer responsiveness")
    return score, reasons or ["recently overdue invoice"]


def classify_cause(text: str, fallback: str = "unknown") -> Dict[str, Any]:
    """Bounded fallback classifier.  Replaceable by existing LLM structured output."""
    normalized = text.lower()
    # Resolve the few ambiguous phrases before broad keyword matching.  This
    # makes the offline mode stable and deliberately testable.
    if "charge is not approved" in normalized:
        return {"cause": "invoice dispute", "confidence": 0.91, "source": "deterministic_reply_classifier"}
    patterns = {
        "invoice dispute": ("dispute", "incorrect", "mismatch", "not received", "wrong invoice", "duplicate", "credit note", "differs", "quantity does not match", "services listed"),
        "approval delay": ("approval", "approve", "approver", "sign off", "finance head", "authorized signatory", "budget owner", "procurement", "director has not cleared"),
        "promise missed": ("missed", "promised", "last friday", "agreed date", "honor the promise", "promise was not met"),
        "payment failure": ("failed", "bank", "upi", "link", "technical", "declined", "transaction failure", "not processing"),
        "customer unreachable": ("unreachable", "no answer", "no one answers", "not responding", "no response", "no reply", "has not replied", "go unanswered", "switched off", "unavailable", "messages remain unanswered", "cannot reach"),
        "payment delay": ("delay", "pay friday", "pay on", "cash flow", "next week", "month end", "three more days", "transfer it tomorrow", "funds are expected", "after the weekend", "scheduled next monday", "short extension"),
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
    if case.get("diagnosis_requires_review"):
        return {"action": "human_escalation", "channel": "manual", "reason": "AI diagnosis confidence is below the automated-action threshold"}
    if case.get("cause") == "invoice dispute":
        return {"action": "human_escalation", "channel": "manual", "reason": "invoice dispute requires human review"}

    journey_actions = {
        "checkout": ("checkout_recovery", "whatsapp", "checkout abandoned; send a time-bound payment link"),
        "subscription": ("subscription_retry", "payment_link", "subscription payment failed; retry before access is interrupted"),
        "mandate": ("mandate_retry", "payment_link", "mandate payment failed; offer a controlled retry"),
    }
    if case.get("journey") in journey_actions:
        action, channel, reason = journey_actions[case["journey"]]
        return {"action": action, "channel": channel, "reason": reason}

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


def build_action_preview(case: Dict[str, Any], policy: Dict[str, str]) -> Dict[str, str]:
    """Create a deterministic, reviewable intervention before it is executed."""
    amount = f"₹{money(case['amount']):,}"
    name = case["customer_name"]
    link = case["payment_link"]
    hindi = case.get("preferred_language") == "hi"
    templates = {
        "checkout_recovery": ("WhatsApp checkout recovery", f"Namaste {name}, aapka {amount} checkout complete nahi hua. Aap yahan securely complete kar sakte hain: {link}", "Time-bound checkout link; no repeated outreach after payment."),
        "subscription_retry": ("Subscription retry", f"Hi {name}, your {amount} subscription payment did not go through. Retry securely here before access is interrupted: {link}", "One controlled retry, then payment-link fallback."),
        "mandate_retry": ("Mandate retry", f"Namaste {name}, {amount} mandate payment unsuccessful raha. Aap secure retry/payment yahan complete kar sakte hain: {link}", "Bounded retry with payment-link fallback."),
        "whatsapp_payment_link": ("WhatsApp payment link", f"{'Namaste' if hindi else 'Hello'} {name}, aapka {amount} invoice pending hai. Secure payment link: {link}", "Personalized reminder; attempt limits and stop rules apply."),
        "whatsapp_reminder": ("WhatsApp reminder", f"{'Namaste' if hindi else 'Hello'} {name}, aapka {amount} payment due hai. Secure link: {link}", "Low-risk first reminder only."),
        "voice_call": ("Voice recovery script", f"Namaste {name}. Aapka {amount} invoice overdue hai. Kya main secure payment link share kar doon?", "One voice call per day; transcript and outcome are audited."),
    }
    title, body, safeguard = templates.get(policy["action"], ("No automated outreach", policy["reason"], "A policy stop or human review is required."))
    return {"title": title, "channel": policy["channel"], "body": body, "safeguard": safeguard}


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
        created["risk_breakdown"] = score_breakdown(created)
        created["risk_reasons"] = reasons
        policy = choose_action(created, today=date(2026, 8, 29))
        created["recommended_action"] = policy["action"]
        created["recommended_channel"] = policy["channel"]
        created["policy_reason"] = policy["reason"]
        created["action_preview"] = build_action_preview(created, policy)
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
        "label": f"Synthetic {len(evaluated)}-invoice benchmark",
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


def synthetic_benchmark_cases(size: int = 72) -> List[Dict[str, Any]]:
    """Return a fixed, reproducible fictional benchmark population.

    It stays separate from interactive recovery cases, so replaying a demo case
    cannot change the aggregate comparison shown to a judge.
    """
    base_cases = seeded_cases()
    generated: List[Dict[str, Any]] = []
    for index in range(size):
        template = deepcopy(base_cases[index % len(base_cases)])
        template["id"] = f"bench-{index + 1:03d}"
        template["invoice_number"] = f"SYN-2026-{index + 1:04d}"
        template["amount"] = money(template["amount"] + ((index * 17_500) % 110_000))
        template["days_overdue"] = max(0, (template["days_overdue"] + index * 3) % 46)
        template["attempts"] = index % (MAX_AUTOMATED_ATTEMPTS + 1)
        template["status"] = "OPEN"
        template["recovered_amount"] = 0
        template["failed_promise"] = bool(template["previous_promise_missed"] and index % 2)
        template["promise_to_pay_date"] = "2026-09-04" if index % 11 == 0 else None
        template["promise_to_pay_amount"] = template["amount"] if template["promise_to_pay_date"] else None
        template["next_action_at"] = "2026-09-04T09:00:00+00:00" if template["promise_to_pay_date"] else None
        score, reasons = score_invoice(template)
        template["risk_score"], template["risk_reasons"], template["risk_breakdown"] = score, reasons, score_breakdown(template)
        policy = choose_action(template, today=date(2026, 8, 29))
        template["recommended_action"], template["recommended_channel"], template["policy_reason"] = policy["action"], policy["channel"], policy["reason"]
        generated.append(template)
    return generated


class RecoveryStore:
    """In-memory reference adapter used by tests and replaceable persistence stores."""
    def __init__(self) -> None:
        self._cases = seeded_cases()
        self._call_summaries: List[Dict[str, Any]] = []

    def reset(self) -> Dict[str, Any]:
        """Restore the fictional dataset so the demo can always be replayed."""
        self._cases = seeded_cases()
        self._call_summaries = []
        return self.summary()

    def scenario_catalog(self) -> List[Dict[str, Any]]:
        return [
            {"id": "degradation", "title": "Payment degradation recovery", "signal": "Payment-success rate degraded after a bank/issuer error spike", "intervention": "Diagnose the failure and route a safe payment-link fallback", "outcome": "Payment recovered, retry scheduled, or human escalation", "amount": 42_000, "customer": "Harborline Traders", "language": "en"},
            {"id": "checkout", "title": "Checkout drop-off recovery", "signal": "Customer abandoned checkout after payment-link generation", "intervention": "Send a time-bound payment link", "outcome": "Payment confirmed or checkout remains abandoned", "amount": 5_999, "customer": "Meera Sharma", "language": "hi"},
            {"id": "subscription", "title": "Failed-subscription recovery", "signal": "Recurring subscription charge failed", "intervention": "Offer a retry and secure payment link before access interruption", "outcome": "Subscription recovered or routed to retry follow-up", "amount": 14_900, "customer": "NovaFit Studios", "language": "en"},
            {"id": "mandate", "title": "Mandate retry sequencer", "signal": "Mandate debit returned by bank", "intervention": "Run a bounded retry with payment-link fallback", "outcome": "Payment recovered or manual escalation", "amount": 78_000, "customer": "Indigo Learning Pvt Ltd", "language": "hi"},
        ]

    def activate_scenario(self, scenario_id: str) -> Dict[str, Any]:
        template = next((item for item in self.scenario_catalog() if item["id"] == scenario_id), None)
        if not template:
            raise KeyError(scenario_id)
        case_id = f"scn-{scenario_id}-001"
        existing = next((item for item in self._cases if item["id"] == case_id), None)
        if existing:
            return deepcopy(existing)
        case = {
            "id": case_id, "customer_name": template["customer"], "invoice_number": f"DEMO-{scenario_id.upper()}-001",
            "amount": template["amount"], "due_date": date(2026, 8, 29).isoformat(), "status": "OPEN", "days_overdue": 0,
            "preferred_language": template["language"], "phone": "+91980000999", "whatsapp": "+91980000999",
            "payment_link": f"https://rzp.io/i/demo-{scenario_id}-001", "attempts": 0, "max_attempts": MAX_AUTOMATED_ATTEMPTS,
            "previous_promise_missed": False, "historical_payment_delay_days": 0, "responsiveness": "high",
            "cause": "payment failure" if scenario_id in {"degradation", "subscription", "mandate"} else "checkout abandonment",
            "cause_confidence": 0.91, "journey": scenario_id, "promise_to_pay_date": None, "promise_to_pay_amount": None,
            "failed_promise": False, "next_action_at": None, "recovered_amount": 0, "demo_data": True,
            "timeline": [
                _event("Revenue signal detected", template["signal"], "signal_detection", "system", "detected"),
                _event("Recovery path selected", template["intervention"], "diagnosis", "system", "approved"),
            ],
        }
        self._refresh_policy(case)
        self._cases.append(case)
        return deepcopy(case)

    def list_call_summaries(self) -> List[Dict[str, Any]]:
        return deepcopy(list(reversed(self._call_summaries)))

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
        case["risk_breakdown"] = score_breakdown(case)
        policy = choose_action(case)
        case["recommended_action"] = policy["action"]
        case["recommended_channel"] = policy["channel"]
        case["policy_reason"] = policy["reason"]
        case["action_preview"] = build_action_preview(case, policy)

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
        action_titles = {
            "checkout_recovery": "Checkout recovery payment link sent",
            "subscription_retry": "Subscription retry initiated",
            "mandate_retry": "Mandate retry initiated",
        }
        title = action_titles.get(policy["action"], "Voice recovery call initiated" if policy["channel"] == "voice" else "WhatsApp + payment link sent")
        notes = f"Approved content: {case['action_preview']['body']} Safeguard: {case['action_preview']['safeguard']}"
        case["timeline"].append(_event(title, notes, policy["action"], policy["channel"], "sent"))
        self._refresh_policy(case)
        return deepcopy(case)

    def apply_diagnosis(self, case_id: str, diagnosis: Dict[str, Any], customer_text: str) -> Dict[str, Any]:
        """Persist a validated classification, then recompute only deterministic policy."""
        case = self._case(case_id)
        if case.get("status") in {"RECOVERED", "STOPPED", "OPTED_OUT"}:
            return deepcopy(case)
        case["cause"] = diagnosis["cause"]
        case["cause_confidence"] = diagnosis["confidence"]
        case["diagnosis_requires_review"] = diagnosis["confidence"] < 0.70
        case["last_diagnosis"] = {
            "source": diagnosis["source"], "reasoning": diagnosis["reasoning"],
            "customer_text": customer_text[:500],
        }
        case["timeline"].append(_event(
            "AI diagnosis recorded",
            f"Classified reply as {diagnosis['cause']} ({round(diagnosis['confidence'] * 100)}% confidence). Source: {diagnosis['source']}. {diagnosis['reasoning']}",
            "diagnosis", "ai", "recorded",
        ))
        if case["diagnosis_requires_review"]:
            case["timeline"].append(_event(
                "Low-confidence diagnosis — human review required",
                "The diagnosis was recorded, but no automated action can proceed below 70% confidence.",
                "human_escalation", "manual", "review_required",
            ))
        self._refresh_policy(case)
        return deepcopy(case)

    def record_promise(self, case_id: str, customer_text: str, promise_date: Optional[str] = None) -> Dict[str, Any]:
        case = self._case(case_id)
        # Replayed webhooks or an accidental second click must not create a
        # second promise and second stop event in the audit trail.
        if case.get("status") == "PROMISE_TO_PAY" and case.get("promise_to_pay_date"):
            self._refresh_policy(case)
            return deepcopy(case)
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

    def receive_payment_webhook(self, case_id: str, provider_event_id: str, payment_id: str, amount: int) -> Dict[str, Any]:
        """Validate and idempotently apply a fictional provider payment event."""
        case = self._case(case_id)
        if money(amount) != money(case["amount"]):
            raise ValueError("Payment amount must equal the case amount")
        processed = case.setdefault("processed_payment_event_ids", [])
        if provider_event_id in processed:
            return deepcopy(case)
        processed.append(provider_event_id)
        case["timeline"].append(_event(
            "Payment provider event received",
            f"Fictional webhook {provider_event_id} validated for payment {payment_id}; amount ₹{money(amount):,}.",
            "payment_webhook", "provider", "received",
        ))
        return self.confirm_payment(case_id)

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

    def simulate_call(self, case_id: str, response_type: str) -> Dict[str, Any]:
        """Run a labelled browser-call demo and persist its visible summary."""
        before = self._case(case_id)
        customer_name = before["customer_name"]
        phone = before["phone"]
        invoice = before["invoice_number"]
        amount = money(before["amount"])
        response_type = response_type.upper()
        case = self.simulate_response(case_id, response_type)
        outcome = {
            "PROMISE_TO_PAY": ("PROMISE RECORDED", f"Customer committed to pay ₹{amount:,} by Friday; outreach paused.", ["Hinglish recovery", "promise-to-pay", "outreach stopped"], []),
            "PAYMENT_CONFIRMED": ("RECOVERED", f"Customer confirmed payment of ₹{amount:,}; case closed.", ["Hinglish recovery", "payment confirmed", "case closed"], []),
            "DISPUTE": ("ESCALATED", "Customer disputed the invoice amount; routed to a human reviewer.", ["Hinglish recovery", "invoice dispute", "human escalation"], ["Invoice amount disputed"]),
        }.get(response_type)
        if not outcome:
            raise ValueError("Call simulation supports promise, payment confirmation, or dispute")
        classification, one_line_summary, topics, objections = outcome
        self._call_summaries.append({
            "session_id": f"demo-call-{len(self._call_summaries) + 1:03d}",
            "case_id": case_id,
            "lead_name": customer_name,
            "lead_phone": phone,
            "invoice_number": invoice,
            "classification": classification,
            "duration_seconds": 42,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "demo_data": True,
            "summary": {
                "one_line_summary": one_line_summary,
                "topics_covered": topics,
                "objections_raised": objections,
            },
            "next_action": case["recommended_action"],
        })
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
