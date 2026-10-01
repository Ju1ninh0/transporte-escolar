"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, tokenStore, type Tokens } from "@/lib/api";
import type { Usuario } from "@/lib/types";

type AuthCtx = {
  user: Usuario | null;
  loading: boolean;
  login: (email: string, senha: string) => Promise<void>;
  logout: () => Promise<void>;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Usuario | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tokenStore.get()) {
      setLoading(false);
      return;
    }
    api<Usuario>("/auth/me")
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, senha: string) => {
    const tokens = await api<Tokens>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, senha }),
    });
    tokenStore.set(tokens);
    setUser(await api<Usuario>("/auth/me"));
  }, []);

  const logout = useCallback(async () => {
    const t = tokenStore.get();
    if (t) {
      await api("/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: t.refresh_token }),
      }).catch(() => {});
    }
    tokenStore.clear();
    setUser(null);
  }, []);

  return <Ctx.Provider value={{ user, loading, login, logout }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth fora do AuthProvider");
  return ctx;
}
