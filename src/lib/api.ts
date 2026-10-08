import { supabase } from "@/lib/supabase";
import type { Usuario } from "@/lib/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Erro da API. `code` é o código estável enviado pelo backend em erros de autenticação:
 * nao_autenticado | token_invalido | token_expirado (401)
 * usuario_nao_cadastrado | usuario_inativo | sem_permissao (403)
 * auth_indisponivel | auth_nao_configurada (503)
 * e "rede" quando o servidor nem respondeu (status 0).
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
  ) {
    super(message);
  }
}

export async function tokenAtual(): Promise<string | undefined> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token;
}

let renovando: Promise<string | undefined> | null = null;
let ultimaRenovacao = 0;

async function renovarSessao(): Promise<string | undefined> {
  if (renovando) return renovando;
  if (Date.now() - ultimaRenovacao < 60000) return undefined;
  ultimaRenovacao = Date.now();
  renovando = (async () => {
    const { data, error } = await supabase.auth.refreshSession();
    if (error) return undefined;
    return data.session?.access_token;
  })().finally(() => {
    renovando = null;
  });
  return renovando;
}

async function request(path: string, init: RequestInit, token?: string) {
  return fetch(`${BASE}/api/v1${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
}

function mensagemPadrao(status: number): string {
  if (status === 401) return "Sua sessão terminou ou é inválida. Entre novamente para continuar.";
  if (status === 403) return "Você não tem permissão para acessar este recurso.";
  if (status >= 500) return "O servidor encontrou um erro. Tente novamente em instantes.";
  return "Algo deu errado. Tente novamente.";
}

/** Cada causa tem a sua mensagem: nada de esconder 401/403/5xx atrás de um texto genérico. */
async function erroDaResposta(res: Response): Promise<ApiError> {
  let message: string | undefined;
  let code: string | undefined;
  try {
    const detail = (await res.json())?.detail;
    if (typeof detail === "string") {
      message = detail;
    } else if (detail && typeof detail === "object" && typeof detail.message === "string") {
      message = detail.message;
      code = typeof detail.code === "string" ? detail.code : undefined;
    } else if (res.status === 422) {
      message = "Verifique os dados informados.";
    }
  } catch {}
  return new ApiError(res.status, message ?? mensagemPadrao(res.status), code);
}

/** Faz a chamada; em 401 tenta renovar a sessão do Supabase uma vez e repete. */
async function executar(path: string, init: RequestInit, token?: string): Promise<Response> {
  try {
    let res = await request(path, init, token);
    if (res.status === 401) {
      const novo = await renovarSessao();
      if (novo) res = await request(path, init, novo);
    }
    return res;
  } catch {
    throw new ApiError(
      0,
      "Não consegui falar com o servidor. Confira sua conexão e se o sistema está no ar.",
      "rede",
    );
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await executar(path, init, await tokenAtual());
  if (!res.ok) throw await erroDaResposta(res);
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

/**
 * GET /auth/me com o access token do Supabase: o FastAPI valida o token, procura
 * usuarios.auth_user_id no PostgreSQL e devolve o Usuario. É a ÚNICA fonte do perfil no frontend.
 */
export async function buscarUsuarioAtual(accessToken: string): Promise<Usuario> {
  const res = await executar("/auth/me", {}, accessToken);
  if (!res.ok) throw await erroDaResposta(res);
  return (await res.json()) as Usuario;
}