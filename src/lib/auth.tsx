"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import type { User } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";
import type { Perfil, Usuario } from "@/lib/types";

type AuthCtx = {
  user: Usuario | null;
  loading: boolean;
  login: (email: string, senha: string) => Promise<Usuario>;
  logout: () => Promise<void>;
};

const PERFIS: Perfil[] = ["ADMIN", "MOTORISTA", "RESPONSAVEL"];

function normalizarPerfil(valor: unknown): Perfil | null {
  const texto = String(valor ?? "").trim().toUpperCase();
  return PERFIS.find((p) => p === texto) ?? null;
}

async function buscarUsuario(authUser: User): Promise<Usuario | null> {
  const { data, error } = await supabase
    .from("Usuarios")
    .select("*")
    .eq("auth_user_id", authUser.id)
    .maybeSingle();

  if (error) {
    console.error("Erro ao buscar perfil:", error);
    return null;
  }

  if (!data) {
    return null;
  }

  const perfil = normalizarPerfil(data.perfil);

  if (!perfil) {
    console.error("Perfil desconhecido para o usuário:", data.perfil);
    return null;
  }

  return {
    id: data.id,
    nome: data.nome,
    email: authUser.email ?? "",
    telefone: data.telefone ?? null,
    perfil,
  };
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Usuario | null>(null);
  const [loading, setLoading] = useState(true);
  const authIdAtual = useRef<string | null>(null);
  const entrando = useRef(false);

  const aplicarSessao = useCallback(async (authUser: User | null) => {
    if (!authUser) {
      authIdAtual.current = null;
      setUser(null);
      return;
    }

    const usuario = await buscarUsuario(authUser);

    if (!usuario) {
      authIdAtual.current = null;
      setUser(null);
      await supabase.auth.signOut({ scope: "local" });
      return;
    }

    authIdAtual.current = authUser.id;
    setUser(usuario);
  }, []);

  useEffect(() => {
    let ativo = true;

    const { data } = supabase.auth.onAuthStateChange((evento, sessao) => {
      if (evento === "SIGNED_OUT") {
        authIdAtual.current = null;
        setUser(null);
        setLoading(false);
        return;
      }

      if (evento !== "INITIAL_SESSION" && evento !== "SIGNED_IN") {
        return;
      }

      if (
        evento === "SIGNED_IN" &&
        (entrando.current || sessao?.user.id === authIdAtual.current)
      ) {
        return;
      }

      const authUser = sessao?.user ?? null;

      setTimeout(async () => {
        await aplicarSessao(authUser);
        if (ativo) {
          setLoading(false);
        }
      }, 0);
    });

    return () => {
      ativo = false;
      data.subscription.unsubscribe();
    };
  }, [aplicarSessao]);

  const login = useCallback(async (email: string, senha: string) => {
    entrando.current = true;

    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password: senha,
      });

      if (error) {
        throw new Error(error.message);
      }

      if (!data.user) {
        throw new Error("Usuário não encontrado.");
      }

      const usuario = await buscarUsuario(data.user);

      if (!usuario) {
        await supabase.auth.signOut({ scope: "local" });
        throw new Error("Perfil do usuário não encontrado.");
      }

      authIdAtual.current = data.user.id;
      setUser(usuario);

      return usuario;
    } finally {
      entrando.current = false;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await supabase.auth.signOut({ scope: "local" });
    } finally {
      authIdAtual.current = null;
      setUser(null);
    }
  }, []);

  return (
    <Ctx.Provider value={{ user, loading, login, logout }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(Ctx);

  if (!ctx) {
    throw new Error("useAuth fora do AuthProvider");
  }

  return ctx;
}