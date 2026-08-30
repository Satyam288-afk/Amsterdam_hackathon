import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

export type DemoRole = "admin" | "user";

export interface DemoUser {
  id: string;
  name: string;
  email: string;
  role: DemoRole;
}

interface AuthContextValue {
  user: DemoUser | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

const STORAGE_KEY = "sambhaash_demo_session";
const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const DEMO_ACCOUNTS = [
  { id: "demo-admin", name: "Sambhaash Admin", email: "admin@sambhaash.demo", password: "Admin@123", role: "admin" as const },
  { id: "demo-user", name: "Recovery Analyst", email: "user@sambhaash.demo", password: "User@123", role: "user" as const },
];

function readSession(): DemoUser | null {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) as DemoUser : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<DemoUser | null>(readSession);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    signIn: async (email, password) => {
      const account = DEMO_ACCOUNTS.find((candidate) => candidate.email === email.trim().toLowerCase() && candidate.password === password);
      if (!account) throw new Error("Use one of the demo accounts shown below.");
      const session: DemoUser = { id: account.id, name: account.name, email: account.email, role: account.role };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
      setUser(session);
    },
    signOut: () => {
      localStorage.removeItem(STORAGE_KEY);
      setUser(null);
    },
  }), [user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useDemoAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useDemoAuth must be used within AuthProvider");
  return context;
}
