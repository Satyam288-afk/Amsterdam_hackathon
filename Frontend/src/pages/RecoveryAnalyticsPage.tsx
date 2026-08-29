import { useEffect, useState } from "react";
import { BarChart3, PhoneCall, ShieldAlert, TrendingUp } from "lucide-react";
import MetricCard from "../components/MetricCard";
import { recoveryDemo } from "../services/recoveryDemo";
import type { RecoveryBenchmark } from "../types/recovery";

const rupees = (value: number) => `₹${value.toLocaleString("en-IN")}`;

export default function RecoveryAnalyticsPage() {
  const [benchmark, setBenchmark] = useState<RecoveryBenchmark | null>(null);
  useEffect(() => { recoveryDemo.getBenchmark().then(setBenchmark); }, []);
  if (!benchmark) return <div className="p-6 text-[#3d2b1f]/70 font-semibold">Calculating recovery analytics…</div>;
  return <div className="space-y-6">
    <div><div className="inline-flex rounded-full bg-[#faedcd] px-3 py-1 text-xs font-black tracking-wider text-[#8b572f]">SYNTHETIC BENCHMARK</div><h1 className="mt-3 text-3xl font-black text-[#2d1e18] font-display">Recovery Analytics</h1><p className="mt-1 text-[#3d2b1f]/70">Reproducible batch calculations from the fictional demo records.</p></div>
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4"><MetricCard label="Invoices Evaluated" value={benchmark.invoices_evaluated} icon={<BarChart3 />} /><MetricCard label="Amount at Risk" value={rupees(benchmark.amount_at_risk)} icon={<TrendingUp />} /><MetricCard label="Promise-to-Pay" value={benchmark.promise_to_pay_count} icon={<PhoneCall />} /><MetricCard label="Escalations" value={benchmark.escalations} icon={<ShieldAlert />} /></div>
    <section className="glass rounded-lg border border-[#faedcd]/60 p-6"><h2 className="text-xl font-black text-[#2d1e18] font-display">How recovery is measured</h2><p className="mt-3 max-w-4xl text-sm leading-6 text-[#3d2b1f]/75">{benchmark.assumption_model}</p><div className="mt-6 grid md:grid-cols-2 gap-5"><div className="rounded-lg bg-[#faedcd]/40 p-5"><p className="text-xs font-bold uppercase tracking-wider text-[#3d2b1f]/65">Baseline — one generic reminder</p><p className="mt-2 text-3xl font-black text-[#2d1e18]">{rupees(benchmark.baseline_recovered)}</p><p className="text-sm text-[#3d2b1f]/65">{benchmark.baseline_recovery_rate}% recovery rate</p></div><div className="rounded-lg bg-emerald-50 border border-emerald-100 p-5"><p className="text-xs font-bold uppercase tracking-wider text-emerald-800/70">Sambhaash — bounded adaptive workflow</p><p className="mt-2 text-3xl font-black text-emerald-800">{rupees(benchmark.sambhaash_recovered)}</p><p className="text-sm text-emerald-800/75">{benchmark.recovery_rate}% recovery rate · {rupees(benchmark.improvement)} incremental recovery</p></div></div></section>
  </div>;
}
