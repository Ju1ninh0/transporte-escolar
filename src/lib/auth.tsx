"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import type { Session } from "@supabase/supabase-js";
import { ApiError, buscarUsuarioAtual } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import type { Perfil, Usuario } from "@/lib/types";

/**
 * Supabase Auth = identidade (sessão, login, logout, access token).
 * Os dados do usuário (perfil, empresa, ativo...) vêm do PostgreSQL via GET /api/v1/auth/me.
 * O frontend NUNCA consulta tabelas do Supabase para descobrir quem o usuário é.
 */
type AuthCtx = {
  user: Usuario | null;
  loading: boolean;
  /** Motivo pelo qual há sessão mas não há usuário carregado (cadastro, servidor, sessão...). */
  authError: string | null;
  login: (email: string, senha: string) => Promise<Usuario>;
  logout: () => Promise<void>;
};

const PERFIS: Perfil[] = ["ADMIN", "MOTORISTA", "RESPONSAVEL"];

function validarUsuario(usuario: Usuario): Usuario {
  if (!PERFIS.includes(usuario.perfil)) {
    throw new ApiError(500, "O servidor devolveu um perfil desconhecido para a sua conta.");
  }
  return usuario;
}

/** 401/403 = a sessão não serve para este sistema; 0/5xx = falha momentânea, mantém a sessão. */
function erroDefinitivo(erro: unknown): boolean {
  return erro instanceof ApiError && (erro.status === 401 || erro.status === 403);
}

function mensagemDoErro(erro: unknown): string {
  return erro instanceof Error ? erro.message : "Não foi possível carregar a sua conta.";
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Usuario | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const authIdAtual = useRef<string | null>(null);
  const entrando = useRef(false);
  const versao = useRef(0);

  const aplicarSessao = useCallback(async (sessao: Session | null) => {
    const minha = ++versao.current;

    if (!sessao) {
      authIdAtual.current = null;
      setUser(null);
      return;
    }

    try {
      const usuario = validarUsuario(await buscarUsuarioAtual(sessao.access_token));
      if (minha !== versao.current) return;
      authIdAtual.current = sessao.user.id;
      setAuthError(null);
      setUser(usuario);
    } catch (erro) {
      if (minha !== versao.current) return;
      console.error("Falha ao carregar o usuário em /auth/me:", erro);
      authIdAtual.current = null;
      setUser(null);
      setAuthError(mensagemDoErro(erro));
      if (erroDefinitivo(erro)) {
        await supabase.auth.signOut({ scope: "local" });
      }
    }
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

      // Não chame métodos do Supabase dentro do callback: adia para fora dele.
      setTimeout(async () => {
        await aplicarSessao(sessao);
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
    versao.current++;
    setAuthError(null);

    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password: senha,
      });

      if (error) {
        throw new Error(error.message);
      }

      const token = data.session?.access_token;

      if (!token || !data.user) {
        throw new Error("Não foi possível iniciar a sessão.");
      }

      let usuario: Usuario;

      try {
        usuario = validarUsuario(await buscarUsuarioAtual(token));
      } catch (erro) {
        await supabase.auth.signOut({ scope: "local" });
        throw erro;
      }

      authIdAtual.current = data.user.id;
      setUser(usuario);

      return usuario;
    } finally {
      entrando.current = false;
    }
  }, []);

  const logout = useCallback(async () => {
    versao.current++;
    try {
      await supabase.auth.signOut({ scope: "local" });
    } finally {
      authIdAtual.current = null;
      setAuthError(null);
      setUser(null);
    }
  }, []);

  return (
    <Ctx.Provider value={{ user, loading, authError, login, logout }}>
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