"use client";
import { Bus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function entrar(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErro(null);
    try {
      await login(email, senha);
      router.replace("/");
    } catch (err) {
      setErro((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-3 text-center">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-900 text-white">
            <Bus className="h-5 w-5" />
          </span>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Transporte Escolar</h1>
            <p className="mt-1 text-sm text-slate-500">Entre com a sua conta para continuar</p>
          </div>
        </div>
        <form onSubmit={entrar} className="card space-y-4 p-6">
          <div>
            <label className="label" htmlFor="email">E-mail</label>
            <input id="email" type="email" required autoComplete="username" className="input"
              value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <label className="label" htmlFor="senha">Senha</label>
            <input id="senha" type="password" required autoComplete="current-password" className="input"
              value={senha} onChange={(e) => setSenha(e.target.value)} />
          </div>
          {erro && <p role="alert" className="callout callout-danger">{erro}</p>}
          <button className="btn w-full" disabled={busy}>{busy ? "Entrando…" : "Entrar"}</button>
        </form>
      </div>
    </main>
  );
}