"""Release-gate smoke test for the fictional Track 03 demo.

Runs without credentials or network calls. It verifies the same core path a
judge sees: activate a scenario, execute only the approved action, record a
simulated outcome, prove the recovery in summaries/analytics, and reset.
"""

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.recovery.engine import RecoveryStore


def main() -> None:
    store = RecoveryStore()

    checkout = store.activate_scenario("checkout")
    assert checkout["recommended_action"] == "checkout_recovery"
    assert checkout["action_preview"]["channel"] == "whatsapp"

    sent = store.execute_action(checkout["id"])
    assert sent["status"] == "IN_PROGRESS"
    assert "Approved content:" in sent["timeline"][-1]["notes"]

    recovered = store.simulate_call(checkout["id"], "PAYMENT_CONFIRMED")
    assert recovered["status"] == "RECOVERED"
    assert recovered["recovered_amount"] == 5_999

    summary = store.summary()
    assert summary["recovered_revenue"] == 5_999
    call_summary = store.list_call_summaries()[0]
    assert call_summary["case_id"] == checkout["id"]
    assert call_summary["classification"] == "RECOVERED"

    reset = store.reset()
    assert reset["recovered_revenue"] == 0
    assert store.list_call_summaries() == []

    print("PASS: scenario → approved action → recovered outcome → analytics → reset")


if __name__ == "__main__":
    main()
