# Sambhaash Recovery — AI Revenue Recovery

> Detect revenue at risk → diagnose the cause → choose a bounded action → recover or escalate → prove the outcome.

Sambhaash Recovery is a demo-ready revenue-recovery agent built for Track 03. It focuses on the full decision loop rather than a dashboard of unconnected features: an explainable risk score creates a policy-bound recovery case, a simulated multilingual conversation produces a customer outcome, and the resulting recovery, stop rule, escalation, audit trail, Conversations entry, and analytics update from the same stateful workflow.

## What is actually implemented

- Stateful FastAPI recovery engine with deterministic scoring and policy rules.
- B2B receivables flagship flow: approved outreach, promise-to-pay, payment confirmation, dispute escalation, and stopping rules.
- Browser-based Hinglish recovery dialer with a clearly labelled simulated transcript. It never places a real call.
- Conversations page populated by simulated-call outcomes.
- Live analytics that reflect the current demo run, separate from the synthetic batch benchmark.
- Scenario Lab for checkout abandonment, failed subscriptions, and mandate-retry recovery. Each launches a real case in the same engine.
- Role-aware demo access: administrators can operate the demo; recovery analysts have a read-only audit view.
- Bounded AI diagnosis: free-form customer replies are classified into a validated cause and confidence, while deterministic policy still owns every action.
- Resettable fictional demo data, backend policy tests, and a production frontend build.

## 60-second judge demo

1. Sign in as **Admin** and open **Dashboard → Run golden demo** for Aarav Mehta (₹84,500 at risk).
2. Show the risk-score breakdown, diagnosis, and approved action.
3. Open the recovery dialer and select **“Payment complete ho gaya”**.
4. Show the case is `RECOVERED`, recovered revenue is ₹84,500, and further outreach is stopped.
5. Open **Conversations** to show the saved call outcome and next action.
6. Open **Analytics** to show the same live recovered amount.
7. Optionally open **Scenario Lab** to launch checkout, subscription, or mandate-retry cases through the same engine.

## Demo access and roles

The local demo starts at `/login`. These accounts exist only in the browser-local demo adapter:

| Role | Sign-in | What it can do |
|---|---|---|
| Administrator | `admin@sambhaash.demo` / `Admin@123` | Launch scenarios, reset the demo, and execute/simulate recovery actions. |
| Recovery analyst | `user@sambhaash.demo` / `User@123` | View cases, score explanations, timelines, Conversations, and analytics. Operational controls are disabled. |

This makes the approval boundary visible during a demo. It is **not production authentication**: the session is stored in local browser storage and is deliberately labelled as demo access. The production implementation below enforces the same boundary using Supabase JWTs and backend authorization.

## Production authentication setup

The project supports real email/password authentication with Supabase. In production mode, Supabase issues the session JWT; the API validates it on every recovery request; and only users whose **server-managed** `app_metadata.recovery_role` is `admin` may mutate recovery state.

1. Create a Supabase project, enable Email/Password authentication, and set your deployed frontend domain as the Site URL / allowed redirect URL.
2. Apply [20260831_role_aware_auth.sql](supabase/migrations/20260831_role_aware_auth.sql) in the Supabase SQL editor (or through the Supabase CLI). It creates a default read-only profile for each authenticated user and enables RLS on those profiles.
3. Set deployment secrets—never commit them:

   ```bash
   # Frontend environment
   VITE_SUPABASE_URL=https://your-project.supabase.co
   VITE_SUPABASE_ANON_KEY=your-anon-key

   # Backend environment
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   AUTH_REQUIRED=true
   CORS_ORIGINS=https://your-frontend-domain.com
   TRUSTED_HOSTS=your-api-domain.com
   ```

4. Invite/create users in Supabase Auth. New users are recovery analysts by default. Promote only trusted operators from secure server-side tooling using the service role—never from the browser:

   ```ts
   await supabase.auth.admin.updateUserById(userId, {
     app_metadata: { recovery_role: "admin" },
   });
   ```

5. Deploy frontend and backend with those variables. The login screen automatically switches from demo accounts to real Supabase credentials when `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are present.

`AUTH_REQUIRED=true` is the production safety switch. Without a valid Supabase JWT, recovery API reads return `401`; operational actions return `403` unless the validated `recovery_role` is `admin`. The in-memory recovery records remain demo data until the next persistence phase.

## Explainable risk score

The score is deterministic, capped at 100, and stored with its full breakdown. No LLM can override this score or the downstream policy.

| Contribution | Points |
|---|---:|
| Event severity: payment failure / checkout abandonment / invoice dispute | +20 / +10 / +25 |
| Days overdue | `min(30, days × 1.5)` |
| Amount tier: ≥₹75k / ≥₹40k / ≥₹10k | +29 / +20 / +10 |
| Prior failed attempts | +8 each, capped at +16 |
| Previous promise missed | +15 |
| Historical payment delay | +8 |
| Low responsiveness | +8 |

For example, a ₹14,900 failed subscription with no overdue days is `20` event-severity points plus `10` amount-tier points: **30/100**. The UI shows every contribution—including zero-value ones—to make the decision auditable.

## Bounded AI diagnosis

An administrator can submit a free-form customer reply on a recovery case. The diagnosis service returns only a schema-validated `cause`, `confidence`, `reasoning`, and `source`; it cannot recommend, execute, or bypass an action. The resulting classification is written to the timeline and the deterministic risk/policy engine recomputes the approved intervention.

By default, the service uses a transparent deterministic reply classifier for a reliable offline demo. To enable Groq structured-output inference, configure `GROQ_API_KEY` and explicitly set `ENABLE_EXTERNAL_LLM_DIAGNOSIS=true`. If Groq is unavailable, malformed, or times out, it safely falls back to the deterministic classifier and labels its source accordingly.

## Policy boundaries

- Maximum automated attempts: **3**
- Maximum voice calls per day: **1**
- Stop automated outreach after payment, opt-out, or a valid promise-to-pay
- Escalate invoice disputes, failed promises, repeated failures, and high-value cases
- Deterministic policy owns payment state, limits, and escalation; AI may assist with language or classification but cannot bypass rules

## Architecture

```mermaid
flowchart LR
  signal[Revenue signal] --> score[Deterministic risk breakdown]
  score --> policy[Bounded policy engine]
  policy --> action[Approved action]
  action --> response[Simulated customer response]
  response --> outcome{Outcome}
  outcome -->|Paid| recovered[Recovered revenue + stop rule]
  outcome -->|Promise| pause[Promise tracker + outreach paused]
  outcome -->|Dispute| human[Human escalation]
  recovered --> proof[Timeline + Conversations + Live Analytics]
  pause --> proof
  human --> proof
```

## Demo data and measurement integrity

All invoice, customer, phone, call, and outcome records bundled with this project are fictional. A simulated call is explicitly labelled as such and does not claim a telephony integration.

The **Live Demo Outcomes** section reflects actions taken in the current in-memory run. The **Synthetic Batch Benchmark** compares a generic-reminder baseline with the bounded workflow across the seeded nine-invoice batch. It is an assumption model calculated in code, not a claim about real merchant outcomes.

## Run locally

Requirements: Python 3.10+ and Node.js **20.19+** (or newer).

```bash
# Terminal 1: backend
cd Backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000

# Terminal 2: frontend
cd Frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, then visit `/login` and sign in as an administrator to run the full demo.

## Verify

```bash
cd Backend
python -m pytest tests/test_recovery_engine.py -q
python scripts/run_recovery_benchmark.py
python scripts/verify_recovery_demo.py

cd ../Frontend
npm run build
```

## Demo API surface

- `GET /api/recovery/summary` — live demo metrics
- `GET /api/recovery/cases` — recovery cases
- `POST /api/recovery/cases/{id}/execute` — approved action
- `POST /api/recovery/cases/{id}/simulate-call` — simulated call outcome + Conversations record
- `GET /api/recovery/call-summaries` — simulated call records
- `GET /api/recovery/scenarios` and `POST /api/recovery/scenarios/{id}/activate` — Scenario Lab
- `POST /api/recovery/demo/reset` — reset only the fictional in-memory dataset

## Production path

The current recovery adapter is intentionally in-memory for a reliable no-credential demo. It now has an optional production authentication path using Supabase JWTs, server-side role checks, and RLS-protected user profiles. A complete production implementation would additionally persist cases and audit events, apply RLS to recovery data, receive verified payment webhooks, use consented communication channels, and retain only the minimum required customer data.
