"use client";
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
    <main className="flex min-h-screen items-center justify-center bg-emerald-50 p-4">
      <form onSubmit={entrar} className="card w-full max-w-sm space-y-4">
        <h1 className="text-center text-2xl font-bold text-emerald-700">🚐 Transporte Escolar</h1>
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
        {erro && <p role="alert" className="text-sm text-red-700">{erro}</p>}
        <button className="btn w-full" disabled={busy}>{busy ? "Entrando…" : "Entrar"}</button>
      </form>
    </main>
  );
}
