"""Run the reproducible, fictional Track 03 recovery benchmark.

Usage (from Backend/):
    python scripts/run_recovery_benchmark.py
    python scripts/run_recovery_benchmark.py --json benchmark-results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.recovery.engine import RecoveryStore, calculate_benchmark


def format_inr(value: int | float) -> str:
    digits = str(int(round(value)))
    if len(digits) <= 3:
        return f"₹{digits}"
    tail = digits[-3:]
    head = digits[:-3]
    groups = []
    while head:
        groups.append(head[-2:])
        head = head[:-2]
    return f"₹{','.join(reversed(groups))},{tail}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DuesPilot's fictional recovery benchmark")
    parser.add_argument("--json", type=Path, help="Optional path to write the calculated JSON result")
    args = parser.parse_args()
    result = calculate_benchmark(RecoveryStore().list_cases())

    print("DuesPilot — Synthetic Recovery Benchmark")
    print("All figures are calculated from the bundled fictional invoice batch.")
    print(f"Invoices evaluated: {result['invoices_evaluated']}")
    print(f"Revenue at risk: {format_inr(result['amount_at_risk'])}")
    print(f"Baseline recovered: {format_inr(result['baseline_recovered'])} ({result['baseline_recovery_rate']}%)")
    print(f"DuesPilot recovered: {format_inr(result['duespilot_recovered'])} ({result['recovery_rate']}%)")
    print(f"Recovery uplift: {format_inr(result['improvement'])}")
    print(f"Average contacts: {result['average_contacts']}")
    print(f"Escalations: {result['escalations']}; promise-to-pay cases: {result['promise_to_pay_count']}")
    print(f"Net recovered value: {format_inr(result['net_recovered_value'])}")
    if args.json:
        args.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"JSON written to: {args.json}")


if __name__ == "__main__":
    main()
