import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowRight, CreditCard, RefreshCw, ShoppingCart } from "lucide-react";
import { recoveryDemo } from "../services/recoveryDemo";

const icons: Record<string, ReactNode> = { degradation: <AlertTriangle />, checkout: <ShoppingCart />, subscription: <CreditCard />, mandate: <RefreshCw /> };
const rupees = (value: number) => `₹${value.toLocaleString("en-IN")}`;

export default function ScenarioLabPage() {
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const navigate = useNavigate();
  useEffect(() => { recoveryDemo.listScenarios().then(setScenarios); }, []);
  const launch = async (id: string) => { setBusy(id); try { const item = await recoveryDemo.activateScenario(id); navigate(`/dashboard/recovery/${item.id}`); } finally { setBusy(null); } };
  return <div className="space-y-6"><div><div className="inline-flex rounded-full bg-[#faedcd] px-3 py-1 text-xs font-black tracking-wider text-[#8b572f]">PHASE 2 · FICTIONAL SCENARIO LAB</div><h1 className="mt-3 text-3xl font-black text-[#2d1e18] font-display">Recover revenue beyond overdue invoices</h1><p className="mt-1 max-w-3xl text-[#3d2b1f]/70">Launch a scenario to create a real case in the same recovery engine. Its decision, controls, audit trail, recovery outcome, Conversations entry, and analytics all use the shared workflow.</p></div><div className="grid gap-5 lg:grid-cols-3">{scenarios.map((scenario) => <section key={scenario.id} className="glass flex flex-col rounded-xl border border-[#faedcd]/60 p-6"><div className="flex h-11 w-11 items-center justify-center rounded-lg bg-[#faedcd] text-[#8b572f]">{icons[scenario.id]}</div><h2 className="mt-4 text-xl font-black text-[#2d1e18] font-display">{scenario.title}</h2><p className="mt-3 text-sm text-[#3d2b1f]/70">{scenario.signal}</p><div className="mt-5 space-y-2 rounded-lg bg-[#fefae0] p-4 text-sm"><p><strong>Intervention:</strong> {scenario.intervention}</p><p><strong>At-risk value:</strong> {rupees(scenario.amount)}</p><p><strong>Proof:</strong> {scenario.outcome}</p></div><button disabled={busy !== null} onClick={() => launch(scenario.id)} className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-[#2d1e18] px-4 py-3 font-bold text-white disabled:opacity-50 cursor-pointer">{busy === scenario.id ? "Launching…" : "Launch scenario"}<ArrowRight size={17} /></button></section>)}</div><p className="text-xs text-[#3d2b1f]/55">All scenarios are fictional demo records. They deliberately reuse the same bounded policy engine; they are not separate mock products.</p></div>;
}
