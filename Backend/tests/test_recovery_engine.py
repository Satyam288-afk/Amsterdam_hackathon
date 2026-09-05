from datetime import date

from services.recovery.engine import RecoveryStore, calculate_benchmark, score_breakdown, score_invoice, synthetic_benchmark_cases
from services.recovery.evaluation import synthetic_corpus
from services.recovery.persistence import SQLiteRecoveryStore


def test_risk_score_has_field_derived_reasons():
    case = RecoveryStore().get_case("rec-001")
    score, reasons = score_invoice(case)
    assert score == 87
    assert reasons == [
        "18 days overdue",
        "high outstanding amount",
        "2 unsuccessful follow-ups",
        "previous promise missed",
    ]


def test_policy_uses_approved_payment_link_action():
    case = RecoveryStore().get_case("rec-001")
    assert case["recommended_action"] == "whatsapp_payment_link"
    assert case["recommended_channel"] == "whatsapp"


def test_max_attempts_escalates_and_prevents_more_automation():
    store = RecoveryStore()
    case = store.get_case("rec-002")
    updated = store.execute_action(case["id"])
    assert updated["status"] == "ESCALATED"
    assert updated["attempts"] == case["attempts"]


def test_payment_closes_case_and_stops_outreach():
    store = RecoveryStore()
    paid = store.confirm_payment("rec-001")
    assert paid["status"] == "RECOVERED"
    assert paid["recovered_amount"] == 84_500
    assert paid["recommended_action"] == "close"


def test_repeated_payment_confirmation_is_idempotent():
    store = RecoveryStore()
    first = store.confirm_payment("rec-001")
    second = store.confirm_payment("rec-001")
    assert second["recovered_amount"] == 84_500
    assert len(second["timeline"]) == len(first["timeline"])


def test_payment_webhook_is_validated_and_idempotent():
    store = RecoveryStore()
    paid = store.receive_payment_webhook("rec-001", "evt-demo-001", "pay-demo-001", 84_500)
    replayed = store.receive_payment_webhook("rec-001", "evt-demo-001", "pay-demo-001", 84_500)
    assert paid["status"] == "RECOVERED"
    assert len(replayed["timeline"]) == len(paid["timeline"])


def test_reset_restores_the_replayable_demo_dataset():
    store = RecoveryStore()
    store.confirm_payment("rec-001")
    reset = store.reset()
    case = store.get_case("rec-001")
    assert reset["recovered_revenue"] == 0
    assert case["status"] == "OPEN"
    assert case["recovered_amount"] == 0


def test_hinglish_promise_is_stored_and_pauses_workflow():
    store = RecoveryStore()
    promised = store.record_promise("rec-001", "Friday ko payment kar denge.")
    assert promised["status"] == "PROMISE_TO_PAY"
    promised_date = date.fromisoformat(promised["promise_to_pay_date"])
    assert promised_date >= date.today()
    assert promised_date.weekday() == 4
    assert promised["promise_to_pay_amount"] == 84_500
    assert promised["recommended_action"] == "pause"


def test_failed_promise_escalates_after_due_date():
    store = RecoveryStore()
    affected = store.mark_failed_promises(date(2026, 9, 5))
    assert affected == 1
    case = store.get_case("rec-003")
    assert case["status"] == "ESCALATED"
    assert case["failed_promise"] is True


def test_dispute_simulation_is_bounded_to_human_escalation():
    store = RecoveryStore()
    updated = store.simulate_response("rec-001", "DISPUTE")
    assert updated["cause"] == "invoice dispute"
    assert updated["status"] == "ESCALATED"
    assert updated["recommended_action"] == "human_escalation"


def test_simulated_call_creates_a_visible_summary():
    store = RecoveryStore()
    store.simulate_call("rec-001", "PROMISE_TO_PAY")
    summary = store.list_call_summaries()[0]
    assert summary["lead_name"] == "Aarav Mehta"
    assert summary["classification"] == "PROMISE RECORDED"
    assert "outreach paused" in summary["summary"]["one_line_summary"]


def test_scenario_activation_reuses_the_recovery_policy_engine():
    store = RecoveryStore()
    checkout = store.activate_scenario("checkout")
    subscription = store.activate_scenario("subscription")
    assert checkout["recommended_action"] == "checkout_recovery"
    assert subscription["recommended_action"] == "subscription_retry"
    assert store.activate_scenario("checkout")["id"] == checkout["id"]


def test_payment_degradation_scenario_is_explicit_and_demoable():
    case = RecoveryStore().activate_scenario("degradation")
    assert case["cause"] == "payment failure"
    assert "degraded" in case["timeline"][0]["notes"]


def test_event_severity_is_explicit_in_the_risk_breakdown():
    subscription = RecoveryStore().activate_scenario("subscription")
    assert subscription["risk_score"] == 30
    assert score_breakdown(subscription)[0] == {"label": "Event severity — payment failure", "points": 20}


def test_action_preview_is_policy_bound_and_saved_in_audit_event():
    store = RecoveryStore()
    case = store.activate_scenario("subscription")
    assert case["action_preview"]["title"] == "Subscription retry"
    updated = store.execute_action(case["id"])
    assert "Approved content:" in updated["timeline"][-1]["notes"]


def test_repeated_promise_response_is_idempotent():
    store = RecoveryStore()
    first = store.simulate_response("rec-001", "PROMISE_TO_PAY")
    second = store.simulate_response("rec-001", "PROMISE_TO_PAY")
    assert second["status"] == "PROMISE_TO_PAY"
    assert len(second["timeline"]) == len(first["timeline"])


def test_benchmark_is_calculated_from_seeded_records():
    benchmark = calculate_benchmark(RecoveryStore().list_cases())
    assert benchmark["invoices_evaluated"] == 9
    assert benchmark["amount_at_risk"] == 1_840_000
    assert benchmark["baseline_recovered"] == 274_000
    assert benchmark["duespilot_recovered"] == 799_500
    assert benchmark["improvement"] == 525_500
    assert benchmark["net_recovered_value"] < benchmark["duespilot_recovered"]


def test_expanded_benchmark_is_reproducible_and_separate_from_demo_cases():
    batch = synthetic_benchmark_cases()
    assert len(batch) == 72
    assert batch[0]["id"] == "bench-001"
    assert batch[-1]["id"] == "bench-072"
    assert calculate_benchmark(batch)["invoices_evaluated"] == 72


def test_ai_diagnosis_is_bounded_and_recomputes_deterministic_policy():
    store = RecoveryStore()
    diagnosis = {"cause": "invoice dispute", "confidence": 0.91, "reasoning": "Customer disputes the amount.", "source": "test"}
    assert diagnosis["cause"] == "invoice dispute"
    updated = store.apply_diagnosis("rec-001", diagnosis, "The invoice amount is wrong; we dispute this charge.")
    assert updated["cause"] == "invoice dispute"
    assert updated["recommended_action"] == "human_escalation"
    assert updated["timeline"][-1]["title"] == "AI diagnosis recorded"


def test_low_confidence_diagnosis_requires_human_review():
    store = RecoveryStore()
    updated = store.apply_diagnosis("rec-001", {"cause": "payment failure", "confidence": 0.62, "reasoning": "Ambiguous customer wording.", "source": "test"}, "Something went wrong")
    assert updated["diagnosis_requires_review"] is True
    assert updated["recommended_action"] == "human_escalation"
    assert updated["timeline"][-1]["outcome"] == "review_required"


def test_synthetic_diagnosis_evaluation_has_sixty_labeled_replies():
    corpus = synthetic_corpus()
    assert len(corpus) == 60
    assert {row["expected_cause"] for row in corpus} == {"payment failure", "approval delay", "invoice dispute", "payment delay", "promise missed", "customer unreachable"}


def test_sqlite_store_preserves_recovery_across_restart(tmp_path):
    path = str(tmp_path / "recovery.sqlite3")
    first = SQLiteRecoveryStore(path)
    first.confirm_payment("rec-001")
    restored = SQLiteRecoveryStore(path)
    assert restored.get_case("rec-001")["status"] == "RECOVERED"
    assert restored.get_case("rec-001")["recovered_amount"] == 84_500
