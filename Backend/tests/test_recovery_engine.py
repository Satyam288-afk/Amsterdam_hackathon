from datetime import date

from services.recovery.engine import RecoveryStore, calculate_benchmark, score_invoice


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


def test_hinglish_promise_is_stored_and_pauses_workflow():
    store = RecoveryStore()
    promised = store.record_promise("rec-001", "Friday ko payment kar denge.")
    assert promised["status"] == "PROMISE_TO_PAY"
    assert promised["promise_to_pay_date"] == "2026-09-04"
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


def test_benchmark_is_calculated_from_seeded_records():
    benchmark = calculate_benchmark(RecoveryStore().list_cases())
    assert benchmark["invoices_evaluated"] == 9
    assert benchmark["amount_at_risk"] == 1_840_000
    assert benchmark["baseline_recovered"] == 274_000
    assert benchmark["sambhaash_recovered"] == 799_500
    assert benchmark["improvement"] == 525_500
    assert benchmark["net_recovered_value"] < benchmark["sambhaash_recovered"]
