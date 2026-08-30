export type RecoveryStatus = "OPEN" | "IN_PROGRESS" | "PROMISE_TO_PAY" | "ESCALATED" | "RECOVERED" | "STOPPED" | "OPTED_OUT";

export interface RecoveryEvent {
  title: string;
  notes: string;
  action: string;
  channel: string;
  outcome: string;
  timestamp: string;
}

export interface RiskBreakdownItem {
  label: string;
  points: number;
}

export interface RecoveryCase {
  id: string;
  customer_name: string;
  invoice_number: string;
  amount: number;
  due_date: string;
  status: RecoveryStatus;
  days_overdue: number;
  preferred_language: string;
  phone: string;
  whatsapp: string;
  payment_link: string;
  risk_score: number;
  risk_reasons: string[];
  risk_breakdown?: RiskBreakdownItem[];
  cause: string;
  cause_confidence: number;
  recommended_action: string;
  recommended_channel: string;
  policy_reason: string;
  attempts: number;
  max_attempts: number;
  promise_to_pay_date?: string | null;
  promise_to_pay_amount?: number | null;
  failed_promise: boolean;
  next_action_at?: string | null;
  recovered_amount: number;
  demo_data: boolean;
  timeline: RecoveryEvent[];
}

export interface RecoverySummary {
  demo_data: boolean;
  revenue_at_risk: number;
  recovered_revenue: number;
  recovery_rate: number;
  open_recovery_cases: number;
  overdue_invoices: number;
  promise_to_pay: number;
  escalations: number;
}

export interface RecoveryBenchmark {
  label: string;
  assumption_model: string;
  invoices_evaluated: number;
  amount_at_risk: number;
  baseline_recovered: number;
  sambhaash_recovered: number;
  baseline_recovery_rate: number;
  recovery_rate: number;
  improvement: number;
  escalations: number;
  promise_to_pay_count: number;
  average_contacts: number;
  net_recovered_value: number;
}
