import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, MessageCircle, PhoneCall, RotateCcw, ShieldAlert } from "lucide-react";
import { recoveryDemo } from "../services/recoveryDemo";
import type { RecoveryCase } from "../types/recovery";

const rupees = (value: number) => `₹${value.toLocaleString("en-IN")}`;
const title = (value: string) => value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
type DemoResponse = "PAYMENT_CONFIRMED" | "PROMISE_TO_PAY" | "DISPUTE" | "PAYMENT_FAILED" | "NO_RESPONSE";

export default function RecoveryCasePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [item, setItem] = useState<RecoveryCase | null>(null);
  const [busy, setBusy] = useState(false);
  const [demoResponse, setDemoResponse] = useState<DemoResponse>("PROMISE_TO_PAY");
  const load = () => id && recoveryDemo.getCase(id).then(setItem);
  useEffect(() => { load(); }, [id]);

  const update = async (operation: () => Promise<RecoveryCase>) => {
    setBusy(true);
    try { setItem(await operation()); } finally { setBusy(false); }
  };
  const reset = async () => {
    setBusy(true);
    try { await recoveryDemo.resetDemo(); navigate("/dashboard/recovery/rec-001"); } finally { setBusy(false); }
  };
  if (!item) return <div className="p-6 text-[#3d2b1f]/70">Loading recovery case…</div>;

  const promiseActive = item.status === "PROMISE_TO_PAY";
  const recovered = item.status === "RECOVERED";
  const terminal = ["RECOVERED", "STOPPED", "OPTED_OUT"].includes(item.status);

  return <div className="space-y-6">
    <div className="flex flex-wrap gap-3">
      <button onClick={() => navigate("/dashboard/recovery")} className="flex items-center gap-2 rounded-lg bg-[#faedcd] px-3 py-2 text-sm font-bold text-[#6e4627] cursor-pointer"><ArrowLeft size={17} />Back to cases</button>
      <button disabled={busy} onClick={reset} className="flex items-center gap-2 rounded-lg border border-[#d4a373]/50 bg-white px-3 py-2 text-sm font-bold text-[#6e4627] disabled:opacity-50 cursor-pointer"><RotateCcw size={16} />Reset demo</button>
    </div>
    <div className="glass rounded-lg border border-[#faedcd]/60 p-6 md:p-8"><div className="flex flex-col gap-4 md:flex-row md:justify-between"><div><div className="text-xs font-black tracking-wider text-[#8b572f]">DEMO DATA · {item.invoice_number}</div><h1 className="mt-2 text-3xl font-black text-[#2d1e18] font-display">{item.customer_name}</h1><p className="mt-1 text-[#3d2b1f]/65">Due {item.due_date} · {item.days_overdue} days overdue · Preferred language: {item.preferred_language === "hi" ? "Hindi / Hinglish" : item.preferred_language}</p></div><div className="text-left md:text-right"><p className="text-3xl font-black text-[#2d1e18]">{rupees(item.amount)}</p><span className="mt-2 inline-block rounded-full bg-[#edf7ef] px-3 py-1 text-xs font-black text-emerald-800">{title(item.status)}</span></div></div></div>
    <div className="grid grid-cols-1 gap-4 md:grid-cols-4"><Card label="Revenue at Risk" value={rupees(item.amount - item.recovered_amount)} /><Card label="Risk Score" value={`${item.risk_score}/100`} danger /><Card label="Attempts" value={`${item.attempts}/${item.max_attempts}`} /><Card label="Recovered" value={rupees(item.recovered_amount)} /></div>
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <section className="glass lg:col-span-2 rounded-lg border border-[#faedcd]/60 p-6"><h2 className="text-xl font-black text-[#2d1e18] font-display">Recovery decision</h2><div className="mt-5 grid gap-5 sm:grid-cols-2"><div><p className="label">Why at risk</p><ul className="mt-2 space-y-2">{item.risk_reasons.map((reason) => <li key={reason} className="text-sm text-[#3d2b1f]/80">• {reason}</li>)}</ul></div><div><p className="label">Cause identified</p><p className="mt-2 font-bold capitalize text-[#2d1e18]">{item.cause}</p><p className="mt-1 text-xs text-[#3d2b1f]/60">Structured confidence: {Math.round(item.cause_confidence * 100)}%</p></div><div><p className="label">Recommended action</p><p className="mt-2 font-bold text-[#2d1e18]">{title(item.recommended_action)}</p><p className="mt-1 text-xs text-[#3d2b1f]/60">{item.policy_reason}</p></div><div><p className="label">Promise-to-pay</p><p className="mt-2 font-bold text-[#2d1e18]">{item.promise_to_pay_date ? `${rupees(item.promise_to_pay_amount || item.amount)} by ${item.promise_to_pay_date}` : "None recorded"}</p><p className="mt-1 text-xs text-[#3d2b1f]/60">{item.next_action_at ? `Next action: ${item.next_action_at.slice(0, 10)}` : "No scheduled follow-up"}</p></div></div></section>
      <section className="glass rounded-lg border border-[#faedcd]/60 p-6"><h2 className="text-xl font-black text-[#2d1e18] font-display">Recovery controls</h2><p className="mt-2 text-sm text-[#3d2b1f]/65">The backend policy is authoritative: payment, opt-out, active promise, daily voice, and attempt limits cannot be overridden.</p>{recovered ? <div className="mt-5 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900"><p className="font-bold">Payment confirmed — outreach stopped.</p><p className="mt-1">This case is closed by the stop rule. Reset the fictional demo to replay it.</p></div> : <div className="mt-5 space-y-3"><p className="text-xs font-black tracking-wide text-[#8b572f]">DEMO FLOW: ACT → CUSTOMER RESPONSE → OUTCOME</p><button disabled={busy || promiseActive || terminal} onClick={() => update(() => recoveryDemo.execute(item.id))} className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#d4a373] px-4 py-3 font-bold text-white disabled:opacity-40 cursor-pointer"><MessageCircle size={18} />Execute approved action</button><div className="rounded-lg border border-[#faedcd] bg-[#fefae0]/70 p-3"><p className="text-xs font-black tracking-wide text-[#6e4627]">SIMULATED CUSTOMER RESPONSE</p><select value={demoResponse} onChange={(event) => setDemoResponse(event.target.value as DemoResponse)} disabled={busy || terminal} className="mt-2 w-full rounded-md border border-[#d4a373]/40 bg-white px-2 py-2 text-sm text-[#3d2b1f]"><option value="PROMISE_TO_PAY">Promise to pay (Hinglish)</option><option value="PAYMENT_CONFIRMED">Payment confirmed</option><option value="DISPUTE">Invoice dispute</option><option value="PAYMENT_FAILED">Payment failed</option><option value="NO_RESPONSE">No response</option></select><button disabled={busy || terminal} onClick={() => update(() => recoveryDemo.simulateResponse(item.id, demoResponse))} className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg bg-[#faedcd] px-4 py-2.5 font-bold text-[#6e4627] disabled:opacity-40 cursor-pointer"><PhoneCall size={17} />Apply response</button></div><button disabled={busy || terminal} onClick={() => update(() => recoveryDemo.confirmPayment(item.id))} className="flex w-full items-center justify-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 font-bold text-emerald-800 disabled:opacity-40 cursor-pointer"><CheckCircle2 size={18} />Simulate payment confirmation</button></div>}<p className="mt-4 text-xs text-[#3d2b1f]/55">Live Twilio, Sarvam, Whisper, Groq, and WhatsApp are optional channels; this stateful demo runs without them.</p></section>
    </div>
    {promiseActive && <div className="flex gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900"><ShieldAlert className="shrink-0" /><div><p className="font-bold">Automated outreach is stopped</p><p className="text-sm">A valid promise-to-pay is active. The system will not contact the customer again before its due date.</p></div></div>}
    <section className="glass rounded-lg border border-[#faedcd]/60 p-6"><h2 className="text-xl font-black text-[#2d1e18] font-display">Action timeline</h2><div className="mt-5 space-y-4">{item.timeline.map((entry, index) => <div className="flex gap-4" key={`${entry.title}-${index}`}><div className="mt-1.5 h-3 w-3 shrink-0 rounded-full bg-[#d4a373]" /><div><p className="font-bold text-[#2d1e18]">{entry.title}</p><p className="text-sm text-[#3d2b1f]/70">{entry.notes}</p><p className="mt-1 text-xs text-[#3d2b1f]/45">{title(entry.channel)} · {title(entry.outcome)}</p></div></div>)}</div></section>
  </div>;
}

function Card({ label, value, danger }: { label: string; value: string; danger?: boolean }) {
  return <div className="glass rounded-lg border border-[#faedcd]/60 p-5"><p className="label">{label}</p><p className={`mt-2 text-2xl font-black ${danger ? "text-rose-700" : "text-[#2d1e18]"}`}>{value}</p></div>;
}
