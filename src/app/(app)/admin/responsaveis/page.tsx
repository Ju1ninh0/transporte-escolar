"use client";
import { useState } from "react";
import { Empty, ErrorBox, Loading, Success } from "@/components/StateViews";
import { api } from "@/lib/api";
import type { Responsavel } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const vazio = { nome: "", email: "", telefone: "", senha: "" };

export default function ResponsaveisPage() {
  const { data, error, loading, reload } = useApi<Responsavel[]>("/responsaveis");
  const [f, setF] = useState(vazio);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const set = (k: keyof typeof vazio) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setF({ ...f, [k]: e.target.value });

  async function criar(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      await api("/responsaveis", {
        method: "POST",
        body: JSON.stringify({ ...f, telefone: f.telefone || null }),
      });
      setF(vazio);
      setMsg({ ok: true, text: "Responsável cadastrado." });
      reload();
    } catch (err) {
      setMsg({ ok: false, text: (err as Error).message });
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Responsáveis</h1>
      <form onSubmit={criar} className="card grid gap-3 md:grid-cols-2">
        <input className="input" placeholder="Nome" required value={f.nome} onChange={set("nome")} />
        <input className="input" type="email" placeholder="E-mail" required value={f.email} onChange={set("email")} />
        <input className="input" placeholder="Telefone" value={f.telefone} onChange={set("telefone")} />
        <input className="input" type="password" placeholder="Senha inicial (mín. 8)" minLength={8} required
          value={f.senha} onChange={set("senha")} />
        <button className="btn md:col-span-2">Cadastrar responsável</button>
        {msg &&
          (msg.ok ? <Success text={msg.text} /> : <p role="alert" className="text-red-700">{msg.text}</p>)}
      </form>
      {loading && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data && data.length === 0 && <Empty text="Nenhum responsável cadastrado." />}
      {data?.map((r) => (
        <div key={r.id} className="card">
          <p className="font-semibold">{r.nome}</p>
          <p className="text-sm text-slate-600">
            {r.email}
            {r.telefone ? ` · ${r.telefone}` : ""}
          </p>
        </div>
      ))}
    </div>
  );
}
