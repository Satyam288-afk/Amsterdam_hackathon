import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { LockKeyhole, ShieldCheck, UserRound } from "lucide-react";
import { useDemoAuth } from "../services/demoAuth";

export default function LoginPage() {
  const { user, signIn, isProductionAuth } = useDemoAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState(isProductionAuth ? "" : "admin@duespilot.demo");
  const [password, setPassword] = useState(isProductionAuth ? "" : "Admin@123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/dashboard/recovery" replace />;

  const fill = (role: "admin" | "user") => {
    if (isProductionAuth) return;
    const isAdmin = role === "admin";
    setEmail(isAdmin ? "admin@duespilot.demo" : "user@duespilot.demo");
    setPassword(isAdmin ? "Admin@123" : "User@123");
    setError("");
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try { await signIn(email, password); navigate("/dashboard/recovery"); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to sign in."); }
    finally { setBusy(false); }
  };

  return <main className="min-h-screen bg-[#fefae0] ambient-glow flex items-center justify-center p-6 text-[#3d2b1f]"><section className="w-full max-w-4xl overflow-hidden rounded-2xl border border-[#d4a373]/30 bg-white/80 shadow-2xl md:grid md:grid-cols-[1.05fr_.95fr]"><div className="bg-[#2d1e18] p-8 text-[#fefae0] md:p-12"><div className="flex items-center gap-3 text-[#f1c27d]"><ShieldCheck size={28} /><span className="font-black tracking-wider">DUESPILOT ACCESS</span></div><h1 className="mt-8 text-4xl font-black font-display leading-tight">Role-aware revenue recovery</h1><p className="mt-5 text-[#fefae0]/75">Admin access can launch scenarios and operate the recovery workflow. Analyst access is deliberately read-only, so the decision trail remains controlled.</p><div className="mt-8 space-y-3 text-sm">{isProductionAuth ? <div className="rounded-lg border border-[#f1c27d]/30 bg-white/10 p-4"><strong>Secure Supabase authentication</strong><p className="mt-1 text-[#fefae0]/65">Use your invited workspace credentials. Roles come from server-managed app metadata.</p></div> : <><button type="button" onClick={() => fill("admin")} className="flex w-full items-center gap-3 rounded-lg border border-[#f1c27d]/30 bg-white/10 p-4 text-left hover:bg-white/15"><ShieldCheck /><span><strong>Admin workspace</strong><br /><span className="text-[#fefae0]/65">Launch scenarios, take actions, reset the demo</span></span></button><button type="button" onClick={() => fill("user")} className="flex w-full items-center gap-3 rounded-lg border border-[#f1c27d]/30 bg-white/10 p-4 text-left hover:bg-white/15"><UserRound /><span><strong>Recovery analyst</strong><br /><span className="text-[#fefae0]/65">Read cases, audit trail, conversations and analytics</span></span></button></>}</div></div><div className="p-8 md:p-12"><p className="text-xs font-black tracking-wider text-[#8b572f]">{isProductionAuth ? "SECURE WORKSPACE ACCESS" : "HACKATHON DEMO ACCESS"}</p><h2 className="mt-2 text-3xl font-black font-display">Sign in</h2><p className="mt-2 text-sm text-[#3d2b1f]/65">{isProductionAuth ? "Use an account created or invited by a workspace administrator." : "Choose an account at left, then sign in to test its boundary."}</p><form onSubmit={submit} className="mt-7 space-y-4"><label className="block text-sm font-bold">Email<input value={email} onChange={(event) => setEmail(event.target.value)} className="mt-1.5 w-full rounded-lg border border-[#d4a373]/40 bg-white px-3 py-3 font-normal outline-none focus:border-[#8b572f]" autoComplete="username" /></label><label className="block text-sm font-bold">Password<input value={password} onChange={(event) => setPassword(event.target.value)} type="password" className="mt-1.5 w-full rounded-lg border border-[#d4a373]/40 bg-white px-3 py-3 font-normal outline-none focus:border-[#8b572f]" autoComplete="current-password" /></label>{error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<button disabled={busy} className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#d4a373] px-4 py-3 font-bold text-white disabled:opacity-60"><LockKeyhole size={17} />{busy ? "Signing in…" : "Sign in to workspace"}</button></form><p className="mt-6 text-xs leading-relaxed text-[#3d2b1f]/50">{isProductionAuth ? "JWT sessions are issued by Supabase. The backend verifies every token and restricts operational recovery endpoints to the server-managed administrator role." : "This is an offline demo role gate stored in this browser—not production identity security. Configure Supabase and AUTH_REQUIRED=true to enable real authentication."}</p></div></section></main>;
}
