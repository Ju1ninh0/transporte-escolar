const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const KEY = "te_tokens";

export type Tokens = { access_token: string; refresh_token: string };

export const tokenStore = {
  get(): Tokens | null {
    if (typeof window === "undefined") return null;
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Tokens) : null;
  },
  set(t: Tokens) {
    window.localStorage.setItem(KEY, JSON.stringify(t));
  },
  clear() {
    window.localStorage.removeItem(KEY);
  },
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
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

async function refresh(): Promise<boolean> {
  const t = tokenStore.get();
  if (!t) return false;
  const res = await request("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: t.refresh_token }),
  });
  if (!res.ok) {
    tokenStore.clear();
    return false;
  }
  tokenStore.set((await res.json()) as Tokens);
  return true;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res = await request(path, init, tokenStore.get()?.access_token);
  if (res.status === 401 && !path.startsWith("/auth/") && (await refresh())) {
    res = await request(path, init, tokenStore.get()?.access_token);
  }
  if (!res.ok) {
    let msg = "Algo deu errado. Tente novamente.";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") msg = body.detail;
      else if (res.status === 422) msg = "Verifique os dados informados.";
    } catch {}
    throw new ApiError(res.status, msg);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}
