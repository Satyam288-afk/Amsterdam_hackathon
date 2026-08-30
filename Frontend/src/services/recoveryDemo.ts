import { apiService } from "./apiService";
import type { RecoveryBenchmark, RecoveryCase, RecoverySummary } from "../types/recovery";

const stamp = "2026-08-29T09:00:00.000Z";
const event = (title: string, notes: string, action = "system", channel = "system", outcome = "recorded") => ({ title, notes, action, channel, outcome, timestamp: stamp });

const rawCases: Array<[string, string, string, number, number, string, number, boolean, string, RecoveryCase["status"]]> = [
  ["rec-001", "Aarav Mehta", "INV-2026-1042", 84500, 18, "hi", 2, true, "approval delay", "OPEN"],
  ["rec-002", "Nila Textiles Pvt Ltd", "INV-2026-1043", 245000, 31, "en", 3, true, "promise missed", "ESCALATED"],
  ["rec-003", "Kaveri Logistics", "INV-2026-1044", 178000, 12, "hi", 1, false, "payment delay", "PROMISE_TO_PAY"],
  ["rec-004", "BlueOrbit Solutions", "INV-2026-1045", 320000, 22, "en", 1, false, "invoice dispute", "OPEN"],
  ["rec-005", "MangoLeaf Retail", "INV-2026-1046", 96000, 9, "ta", 0, false, "payment failure", "OPEN"],
  ["rec-006", "Vardhan Components", "INV-2026-1047", 210000, 40, "hi", 3, true, "customer unreachable", "ESCALATED"],
  ["rec-007", "Northstar Consulting", "INV-2026-1048", 156000, 15, "en", 1, false, "approval delay", "OPEN"],
  ["rec-008", "Sampoorna Foods", "INV-2026-1049", 285000, 27, "hi", 2, false, "payment delay", "OPEN"],
  ["rec-009", "Delta Equipment", "INV-2026-1050", 265500, 6, "en", 0, false, "unknown", "OPEN"],
];

const risk = (amount: number, days: number, attempts: number, missed: boolean) => Math.min(100, Math.round(days * 1.5) + (amount >= 75000 ? 29 : amount >= 40000 ? 20 : amount >= 10000 ? 10 : 0) + Math.min(16, attempts * 8) + (missed ? 15 : 0));
const reasons = (amount: number, days: number, attempts: number, missed: boolean) => [
  `${days} days overdue`,
  ...(amount >= 75000 ? ["high outstanding amount"] : amount >= 40000 ? ["material outstanding amount"] : []),
  ...(attempts ? [`${attempts} unsuccessful follow-up${attempts === 1 ? "" : "s"}`] : []),
  ...(missed ? ["previous promise missed"] : []),
];

const makeCases = (): RecoveryCase[] => rawCases.map(([id, customer_name, invoice_number, amount, days_overdue, preferred_language, attempts, previousMissed, cause, status], index) => {
  const risk_score = risk(amount, days_overdue, attempts, previousMissed);
  const escalated = status === "ESCALATED";
  const promise = id === "rec-003";
  const action = escalated ? "human_escalation" : promise ? "pause" : "whatsapp_payment_link";
  return {
    id, customer_name, invoice_number, amount, due_date: new Date(Date.UTC(2026, 7, 29) - days_overdue * 86_400_000).toISOString().slice(0, 10),
    status, days_overdue, preferred_language, phone: `+91980000${100 + index}`, whatsapp: `+91980000${100 + index}`,
    payment_link: `https://rzp.io/i/demo-${invoice_number.toLowerCase()}`, risk_score, risk_reasons: reasons(amount, days_overdue, attempts, previousMissed),
    cause, cause_confidence: cause === "unknown" ? 0.5 : 0.91, recommended_action: action,
    recommended_channel: action === "human_escalation" ? "manual" : action === "pause" ? "none" : "whatsapp",
    policy_reason: escalated ? "high value or failed promise" : promise ? "valid promise-to-pay is active" : "personalized payment-link outreach",
    attempts, max_attempts: 3, promise_to_pay_date: promise ? "2026-09-04" : null, promise_to_pay_amount: promise ? amount : null,
    failed_promise: escalated, next_action_at: promise ? "2026-09-04T09:00:00+00:00" : null, recovered_amount: 0, demo_data: true,
    timeline: [
      event("Risk detected", `₹${amount.toLocaleString("en-IN")} at risk`, "risk_score"),
      event("Cause identified", cause.replace(/\b\w/g, (letter) => letter.toUpperCase()), "diagnosis"),
      ...(id === "rec-001" ? [event("WhatsApp reminder sent", "First reminder delivered with secure payment link", "whatsapp_payment_link", "whatsapp", "sent"), event("Customer responded", "Approval is pending; customer asked for a Friday follow-up", "customer_reply", "whatsapp", "received")] : []),
      ...(promise ? [event("Promise to pay recorded", `₹${amount.toLocaleString("en-IN")} by Friday; automated outreach paused`, "promise_to_pay", "voice")] : []),
      ...(escalated ? [event("Human escalation", "Automated outreach limit reached or promise failed", "human_escalation", "manual", "escalated")] : []),
    ],
  };
});

let fallbackCases = makeCases();
let fallbackCallSummaries: any[] = [];
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

const summary = (): RecoverySummary => {
  const open = fallbackCases.filter((item) => !["RECOVERED", "STOPPED", "OPTED_OUT"].includes(item.status));
  const recovered_revenue = fallbackCases.reduce((sum, item) => sum + item.recovered_amount, 0);
  const revenue_at_risk = open.reduce((sum, item) => sum + item.amount - item.recovered_amount, 0);
  return { demo_data: true, revenue_at_risk, recovered_revenue, recovery_rate: recovered_revenue ? Number((recovered_revenue / (revenue_at_risk + recovered_revenue) * 100).toFixed(1)) : 0, open_recovery_cases: open.length, overdue_invoices: open.length, promise_to_pay: fallbackCases.filter((item) => item.status === "PROMISE_TO_PAY").length, escalations: fallbackCases.filter((item) => item.status === "ESCALATED").length };
};

const benchmark = (): RecoveryBenchmark => {
  const atRisk = rawCases.reduce((total, row) => total + row[3], 0);
  const baseline = rawCases.filter((row) => ["payment delay", "payment failure"].includes(row[8]) && row[4] < 15).reduce((total, row) => total + row[3], 0);
  const sambhaash = rawCases.filter((row) => ["payment delay", "payment failure", "approval delay"].includes(row[8]) && row[9] !== "ESCALATED").reduce((total, row) => total + row[3], 0);
  const contacts = rawCases.reduce((total, row) => total + Math.min(row[6] + 1, 3), 0);
  return { label: "Synthetic benchmark", assumption_model: "Baseline sends one generic reminder. Sambhaash applies deterministic risk, diagnosis, approved intervention, and stop rules to fictional invoices.", invoices_evaluated: rawCases.length, amount_at_risk: atRisk, baseline_recovered: baseline, sambhaash_recovered: sambhaash, baseline_recovery_rate: Number((baseline / atRisk * 100).toFixed(1)), recovery_rate: Number((sambhaash / atRisk * 100).toFixed(1)), improvement: sambhaash - baseline, escalations: rawCases.filter((row) => row[9] === "ESCALATED").length, promise_to_pay_count: 1, average_contacts: Number((contacts / rawCases.length).toFixed(1)), net_recovered_value: sambhaash - contacts * 12 };
};

const fallbackCase = (id: string) => {
  const found = fallbackCases.find((item) => item.id === id);
  if (!found) throw new Error("Recovery case not found");
  return found;
};

export const recoveryDemo = {
  async resetDemo(): Promise<RecoverySummary> {
    try {
      return (await apiService.api.post<{ summary: RecoverySummary }>("/api/recovery/demo/reset")).data.summary;
    } catch {
      fallbackCases = makeCases();
      fallbackCallSummaries = [];
      return clone(summary());
    }
  },
  async getSummary(): Promise<RecoverySummary> { try { return (await apiService.api.get<RecoverySummary>("/api/recovery/summary")).data; } catch { return clone(summary()); } },
  async listCases(): Promise<RecoveryCase[]> { try { return (await apiService.api.get<{ cases: RecoveryCase[] }>("/api/recovery/cases")).data.cases; } catch { return clone(fallbackCases); } },
  async getCase(id: string): Promise<RecoveryCase> { try { return (await apiService.api.get<RecoveryCase>(`/api/recovery/cases/${id}`)).data; } catch { return clone(fallbackCase(id)); } },
  async getBenchmark(): Promise<RecoveryBenchmark> { try { return (await apiService.api.get<RecoveryBenchmark>("/api/recovery/benchmark")).data; } catch { return benchmark(); } },
  async listCallSummaries(): Promise<any[]> { try { return (await apiService.api.get<{ data: any[] }>("/api/recovery/call-summaries")).data.data; } catch { return clone(fallbackCallSummaries); } },
  async execute(id: string): Promise<RecoveryCase> {
    try { return (await apiService.api.post<RecoveryCase>(`/api/recovery/cases/${id}/execute`)).data; } catch {
      const item = fallbackCase(id); item.attempts += 1; item.status = "IN_PROGRESS"; item.timeline.push(event("WhatsApp + payment link sent", "Demo action recorded; live WhatsApp remains optional.", "whatsapp_payment_link", "whatsapp", "sent")); return clone(item);
    }
  },
  async recordPromise(id: string, customerText: string): Promise<RecoveryCase> {
    try { return (await apiService.api.post<RecoveryCase>(`/api/recovery/cases/${id}/promise`, { customer_text: customerText })).data; } catch {
      const item = fallbackCase(id); item.status = "PROMISE_TO_PAY"; item.promise_to_pay_date = "2026-09-04"; item.promise_to_pay_amount = item.amount; item.next_action_at = "2026-09-04T09:00:00+00:00"; item.recommended_action = "pause"; item.recommended_channel = "none"; item.policy_reason = "valid promise-to-pay is active"; item.timeline.push(event("Promise to pay recorded", `₹${item.amount.toLocaleString("en-IN")} by 2026-09-04; automated outreach stopped`, "promise_to_pay", "voice"), event("Automated outreach stopped", "Valid promise-to-pay is active", "pause", "system", "stopped")); return clone(item);
    }
  },
  async confirmPayment(id: string): Promise<RecoveryCase> {
    try { return (await apiService.api.post<RecoveryCase>(`/api/recovery/cases/${id}/payment-confirmed`)).data; } catch {
      const item = fallbackCase(id); item.status = "RECOVERED"; item.recovered_amount = item.amount; item.recommended_action = "close"; item.recommended_channel = "none"; item.policy_reason = "payment confirmed"; item.timeline.push(event("Payment confirmed", `₹${item.amount.toLocaleString("en-IN")} recovered`, "payment_confirmation", "payment_link", "recovered"), event("Case recovered", "No further outreach permitted", "close", "system", "closed")); return clone(item);
    }
  },
  async simulateResponse(id: string, responseType: "PAYMENT_CONFIRMED" | "PROMISE_TO_PAY" | "DISPUTE" | "PAYMENT_FAILED" | "NO_RESPONSE"): Promise<RecoveryCase> {
    try { return (await apiService.api.post<RecoveryCase>(`/api/recovery/cases/${id}/simulate-response`, { response_type: responseType })).data; } catch {
      if (responseType === "PAYMENT_CONFIRMED") return this.confirmPayment(id);
      if (responseType === "PROMISE_TO_PAY") return this.recordPromise(id, "Friday ko payment kar denge.");
      const item = fallbackCase(id);
      if (["RECOVERED", "STOPPED", "OPTED_OUT"].includes(item.status)) return clone(item);
      if (responseType === "DISPUTE") {
        item.cause = "invoice dispute"; item.cause_confidence = 0.91; item.status = "ESCALATED"; item.recommended_action = "human_escalation"; item.recommended_channel = "manual"; item.policy_reason = "invoice dispute requires collections review";
        item.timeline.push(event("Invoice dispute detected", "Demo customer response requires human review", "diagnosis", "system", "received"), event("Human escalation", "Invoice dispute requires collections review", "human_escalation", "manual", "escalated"));
      } else if (responseType === "PAYMENT_FAILED") {
        item.cause = "payment failure"; item.cause_confidence = 0.91; item.timeline.push(event("Payment failure reported", "Customer reported a payment issue; approved recovery policy recalculated", "customer_reply", "payment_link", "received"));
      } else {
        item.timeline.push(event("No customer response", "No reply was recorded; the next action remains policy controlled", "no_response", "system", "recorded"));
      }
      return clone(item);
    }
  },
  async simulateCall(id: string, responseType: "PAYMENT_CONFIRMED" | "PROMISE_TO_PAY" | "DISPUTE"): Promise<RecoveryCase> {
    try { return (await apiService.api.post<RecoveryCase>(`/api/recovery/cases/${id}/simulate-call`, { response_type: responseType })).data; } catch {
      const caseItem = await this.simulateResponse(id, responseType);
      const details = responseType === "PROMISE_TO_PAY" ? ["PROMISE RECORDED", `Customer committed to pay ₹${caseItem.amount.toLocaleString("en-IN")} by Friday; outreach paused.`, ["Hinglish recovery", "promise-to-pay", "outreach stopped"], []] : responseType === "PAYMENT_CONFIRMED" ? ["RECOVERED", `Customer confirmed payment of ₹${caseItem.amount.toLocaleString("en-IN")}; case closed.`, ["Hinglish recovery", "payment confirmed", "case closed"], []] : ["ESCALATED", "Customer disputed the invoice amount; routed to a human reviewer.", ["Hinglish recovery", "invoice dispute", "human escalation"], ["Invoice amount disputed"]];
      fallbackCallSummaries.unshift({ session_id: `demo-call-${fallbackCallSummaries.length + 1}`, case_id: id, lead_name: caseItem.customer_name, lead_phone: caseItem.phone, invoice_number: caseItem.invoice_number, classification: details[0], duration_seconds: 42, created_at: new Date().toISOString(), demo_data: true, next_action: caseItem.recommended_action, summary: { one_line_summary: details[1], topics_covered: details[2], objections_raised: details[3] } });
      return caseItem;
    }
  },
};
