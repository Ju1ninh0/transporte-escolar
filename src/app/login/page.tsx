"use client";
import { Bus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Loading } from "@/components/StateViews";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { homePorPerfil } from "@/lib/types";

function mensagemAmigavel(erro: unknown) {
  // Erros do nosso servidor (sem cadastro, conta inativa, servidor fora do ar...) já vêm com a
  // mensagem certa: mostramos como estão, sem trocar por um texto genérico.
  if (erro instanceof ApiError) {
    return erro.message;
  }
  const texto = erro instanceof Error ? erro.message : "";
  if (texto.includes("Invalid login credentials")) {
    return "E-mail ou senha incorretos. Confira e tente de novo.";
  }
  if (texto.includes("Email not confirmed")) {
    return "Seu e-mail ainda não foi confirmado. Veja sua caixa de entrada.";
  }
  if (texto.toLowerCase().includes("rate limit") || texto.includes("too many")) {
    return "Muitas tentativas seguidas. Aguarde um pouco e tente novamente.";
  }
  return "Não foi possível entrar agora. Tente novamente em instantes.";
}

export default function LoginPage() {
  const { login, user, loading, authError } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && user) {
      router.replace(homePorPerfil[user.perfil]);
    }
  }, [loading, user, router]);

  async function entrar(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErro(null);
    try {
      const usuario = await login(email.trim(), senha);
      router.replace(homePorPerfil[usuario.perfil]);
    } catch (err) {
      setErro(mensagemAmigavel(err));
      setBusy(false);
    }
  }

  if (loading || user) {
    return <Loading />;
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
            <p className="mt-1 text-sm text-slate-500">Que bom ter você de volta. Entre com a sua conta para continuar.</p>
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
          {(erro ?? authError) && (
            <p role="alert" className="callout callout-danger">{erro ?? authError}</p>
          )}
          <button className="btn w-full" disabled={busy}>{busy ? "Entrando…" : "Entrar"}</button>
        </form>
      </div>
    </main>
  );
}