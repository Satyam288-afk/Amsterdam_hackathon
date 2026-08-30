import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "";
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || "";

// Recovery demo mode must work without cloud credentials. A local inert client
// keeps legacy auth-dependent components mountable while no real Supabase
// request can be made until both environment variables are supplied.
const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

export const supabase = createClient(
  isSupabaseConfigured ? supabaseUrl : "http://127.0.0.1:54321",
  isSupabaseConfigured ? supabaseAnonKey : "offline-demo-anon-key",
  isSupabaseConfigured
    ? undefined
    : {
        auth: {
          persistSession: false,
          autoRefreshToken: false,
          detectSessionInUrl: false,
        },
      },
);
