import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { isSupabaseConfigured, supabase } from "./supabase";

export type DemoRole = "admin" | "user";

export interface DemoUser {
  id: string;
  name: string;
  email: string;
  role: DemoRole;
}

interface AuthContextValue {
  user: DemoUser | null;
  loading: boolean;
  isProductionAuth: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

const STORAGE_KEY = "sambhaash_demo_session";
const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const DEMO_ACCOUNTS = [
  { id: "demo-admin", name: "DuesPilot Admin", email: "admin@duespilot.demo", password: "Admin@123", role: "admin" as const },
  { id: "demo-user", name: "Recovery Analyst", email: "user@duespilot.demo", password: "User@123", role: "user" as const },
];

function readSession(): DemoUser | null {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return null;
    const session = JSON.parse(saved) as DemoUser;
    // Keep existing browser sessions through the product rename.
    if (session.id === "demo-admin") session.name = "DuesPilot Admin";
    if (session.id === "demo-admin" || session.id === "demo-user") {
      session.email = session.email.replace("@sambhaash.demo", "@duespilot.demo");
    }
    return session;
  } catch {
    return null;
  }
}

function fromSupabaseUser(user: { id: string; email?: string; user_metadata?: Record<string, unknown>; app_metadata?: Record<string, unknown> }): DemoUser {
  // App metadata is minted only by privileged server-side tooling. Never trust
  // client-editable user_metadata to decide authorization.
  const role = user.app_metadata?.recovery_role === "admin" ? "admin" : "user";
  const fullName = typeof user.user_metadata?.full_name === "string" ? user.user_metadata.full_name : "";
  return { id: user.id, name: fullName || user.email?.split("@")[0] || "Recovery user", email: user.email || "", role };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<DemoUser | null>(readSession);
  const [loading, setLoading] = useState(isSupabaseConfigured);

  useEffect(() => {
    if (!isSupabaseConfigured) { setLoading(false); return; }
    let live = true;
    supabase.auth.getSession().then(({ data }) => {
      if (live) { setUser(data.session?.user ? fromSupabaseUser(data.session.user) : null); setLoading(false); }
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (live) { setUser(session?.user ? fromSupabaseUser(session.user) : null); setLoading(false); }
    });
    return () => { live = false; subscription.unsubscribe(); };
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    loading,
    isProductionAuth: isSupabaseConfigured,
    signIn: async (email, password) => {
      if (isSupabaseConfigured) {
        const { data, error } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
        if (error || !data.user) throw new Error(error?.message || "Unable to sign in.");
        setUser(fromSupabaseUser(data.user));
        return;
      }
      const normalizedEmail = email.trim().toLowerCase().replace("@sambhaash.demo", "@duespilot.demo");
      const account = DEMO_ACCOUNTS.find((candidate) => candidate.email === normalizedEmail && candidate.password === password);
      if (!account) throw new Error("Use one of the demo accounts shown below.");
      const session: DemoUser = { id: account.id, name: account.name, email: account.email, role: account.role };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
      setUser(session);
    },
    signOut: () => {
      localStorage.removeItem(STORAGE_KEY);
      setUser(null);
      if (isSupabaseConfigured) void supabase.auth.signOut();
    },
  }), [user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useDemoAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useDemoAuth must be used within AuthProvider");
  return context;
}
