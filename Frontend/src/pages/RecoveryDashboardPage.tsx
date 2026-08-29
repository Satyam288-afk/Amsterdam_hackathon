import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, BadgeIndianRupee, CheckCircle2, Clock3, Handshake, ShieldAlert } from "lucide-react";
import MetricCard from "../components/MetricCard";
import DataTable from "../components/DataTable";
import { recoveryDemo } from "../services/recoveryDemo";
import type { RecoveryCase, RecoverySummary } from "../types/recovery";

const rupees = (value: number) => `₹${value.toLocaleString("en-IN")}`;
const title = (value: string) => value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

export default function RecoveryDashboardPage() {
  const [cases, setCases] = useState<RecoveryCase[]>([]);
  const [metrics, setMetrics] = useState<RecoverySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([recoveryDemo.listCases(), recoveryDemo.getSummary()]).then(([allCases, summary]) => {
      setCases(allCases); setMetrics(summary); setLoading(false);
    });
  }, []);

  if (loading || !metrics) return <div className="p-6 text-[#3d2b1f]/70 font-semibold">Loading recovery workspace…</div>;
  const columns = [
    { key: "customer_name" as keyof RecoveryCase, label: "Customer", sortable: true, render: (_: unknown, row: RecoveryCase) => <div><p className="font-bold">{row.customer_name}</p><p className="text-xs text-gray-500">{row.invoice_number}</p></div> },
    { key: "amount" as keyof RecoveryCase, label: "Amount", sortable: true, render: (value: unknown) => <span className="font-bold">{rupees(Number(value))}</span> },
    { key: "days_overdue" as keyof RecoveryCase, label: "Days Overdue", sortable: true, render: (value: unknown) => `${value} days` },
    { key: "risk_score" as keyof RecoveryCase, label: "Risk", sortable: true, render: (value: unknown) => <span className={Number(value) > 70 ? "font-black text-rose-700" : "font-black text-amber-700"}>{value}/100</span> },
    { key: "cause" as keyof RecoveryCase, label: "Reason", render: (value: unknown) => <span className="capitalize">{String(value)}</span> },
    { key: "recommended_action" as keyof RecoveryCase, label: "Next Action", render: (value: unknown) => <span className="text-xs font-bold px-2 py-1 rounded bg-[#faedcd] text-[#6e4627]">{title(String(value))}</span> },
    { key: "status" as keyof RecoveryCase, label: "Status", render: (value: unknown) => <span className="text-xs font-bold px-2 py-1 rounded bg-[#edf7ef] text-emerald-800">{title(String(value))}</span> },
  ];
  return <div className="space-y-6">
    <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
      <div><div className="inline-flex rounded-full bg-[#faedcd] px-3 py-1 text-xs font-black tracking-wider text-[#8b572f]">DEMO DATA · FICTIONAL INVOICES</div><h1 className="mt-3 text-3xl font-black text-[#2d1e18] font-display">AI Revenue Recovery</h1><p className="mt-1 text-[#3d2b1f]/70">Detect → Diagnose → Decide → Act → Recover</p></div>
      <p className="max-w-sm text-sm text-[#3d2b1f]/70">Bounded B2B receivables workflows. Customer data is not required to run this demo.</p>
    </div>
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      <MetricCard label="Revenue at Risk" value={rupees(metrics.revenue_at_risk)} icon={<AlertTriangle />} trend="down" trendValue="Open receivables" />
      <MetricCard label="Recovered Revenue" value={rupees(metrics.recovered_revenue)} icon={<BadgeIndianRupee />} trend="up" trendValue={`${metrics.recovery_rate}% recovery rate`} />
      <MetricCard label="Open Recovery Cases" value={metrics.open_recovery_cases} icon={<Clock3 />} />
      <MetricCard label="Promise-to-Pay" value={metrics.promise_to_pay} icon={<Handshake />} />
      <MetricCard label="Overdue Invoices" value={metrics.overdue_invoices} icon={<AlertTriangle />} />
      <MetricCard label="Escalations" value={metrics.escalations} icon={<ShieldAlert />} />
      <MetricCard label="Automated Attempt Limit" value="3" icon={<CheckCircle2 />} trend="neutral" trendValue="Enforced server-side" />
    </div>
    <div className="glass rounded-lg border border-[#faedcd]/60 p-4 md:p-6"><div className="mb-5"><h2 className="text-xl font-black text-[#2d1e18] font-display">Recovery Cases</h2><p className="text-sm text-[#3d2b1f]/65">Open a case to inspect evidence, policy, action history, and recovery outcome.</p></div><DataTable columns={columns} data={cases} rowKey="id" onRowClick={(item: RecoveryCase) => navigate(`/dashboard/recovery/${item.id}`)} /></div>
  </div>;
}
