# Sambhaash Recovery — Track 03 Submission Pack

## One-line pitch

Sambhaash Recovery detects revenue at risk, chooses a policy-bound recovery intervention, and proves the outcome with stopping rules, an audit trail, Conversations records, and live demo analytics.

## Problem

Revenue loss is rarely one clean failure: a checkout is abandoned, a subscription payment fails, a mandate returns, or an invoice becomes overdue. Teams need more than a reminder—they need a controlled workflow that knows when to act, when to stop, and when to escalate.

## What we built

- A deterministic, explainable risk engine with an on-screen score breakdown.
- A bounded policy engine that selects approved actions and enforces contact limits, promise-to-pay pauses, payment stops, and human escalation.
- A simulated Hinglish recovery dialer that records a real workflow outcome in the app.
- A B2B receivables flagship flow plus checkout, subscription, and mandate-retry scenarios in one shared engine.
- Cross-screen proof: a case action updates the audit timeline, Conversations, and Live Demo Outcomes.

## 90-second demo script

1. **Problem (10s):** “Revenue recovery is not just sending reminders. We must detect risk, select an intervention, and stop safely when the customer responds.”
2. **Detect and decide (20s):** Open Aarav Mehta. Show the risk-score breakdown, cause, and policy-bound recommendation.
3. **Act (20s):** Open the recovery dialer. Explain it is an in-browser simulation. Select “Payment complete ho gaya.”
4. **Prove (20s):** Show `RECOVERED`, ₹84,500 recovered, the no-more-outreach stop rule, and the action timeline.
5. **Audit and outcome (10s):** Open Conversations, then Analytics, to show the call outcome and live recovered revenue.
6. **Breadth (10s):** Open Scenario Lab: checkout abandonment, failed subscription, and mandate retry all reuse the same engine and controls.

## Engineering evidence

| Evidence | What it proves |
|---|---|
| Risk-score breakdown | Decisions are explainable; event severity is separate from overdue/amount signals. |
| Policy-bound intervention preview | The shown message comes from the same policy that authorizes execution. |
| Idempotent payment and promise handlers | Replayed customer events do not create duplicate money recovery or promise records. |
| Action timeline + Conversations | Every simulated call outcome leaves an auditable record. |
| Live Demo Outcomes | Current-run recovery metrics update after a simulated outcome. |
| Synthetic Batch Benchmark | A transparent, reproducible comparison across nine fictional invoices. |
| Release-gate script | Core scenario → action → recovery → analytics → reset path is automatically verified. |

## Honest scope

- All bundled customers, invoices, phone numbers, calls, and outcomes are fictional demo data.
- The dialer is an explicit in-browser simulation; it does not place a real call.
- The batch benchmark is a coded assumption model, not a claim about merchant performance.
- The demo adapter is in memory. Production would persist auditable events, authenticate users, ingest verified payment webhooks, and use consented communications.

## Final pre-submit checklist

- [ ] Start backend and frontend locally.
- [ ] Run `python Backend/scripts/verify_recovery_demo.py`.
- [ ] Run `python Backend/scripts/run_recovery_benchmark.py`.
- [ ] Reset demo before recording or presenting.
- [ ] Run the 90-second script once without narration notes.
- [ ] Record/upload a demo video and add its real URL to the submission form.
- [ ] Use only claims supported by the app and this document.

## Quick links

- Product and local run instructions: [README.md](README.md)
- End-to-end demo release gate: [verify_recovery_demo.py](Backend/scripts/verify_recovery_demo.py)
- Deterministic recovery engine: [engine.py](Backend/services/recovery/engine.py)
