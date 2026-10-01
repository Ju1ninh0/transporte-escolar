"use client";
import { useState } from "react";
import { Empty, ErrorBox, Loading, Success } from "@/components/StateViews";
import { api } from "@/lib/api";
import { fmtData, type Aluno, type Responsavel } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const vazio = { nome: "", data_nascimento: "", escola: "", serie: "", responsavel_id: "" };

export default function AlunosPage() {
  const alunos = useApi<Aluno[]>("/alunos");
  const resp = useApi<Responsavel[]>("/responsaveis");
  const [f, setF] = useState(vazio);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const set = (k: keyof typeof vazio) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setF({ ...f, [k]: e.target.value });
  const nomeResp = (id: number) => resp.data?.find((r) => r.id === id)?.nome ?? "—";

  async function criar(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      await api("/alunos", {
        method: "POST",
        body: JSON.stringify({ ...f, serie: f.serie || null, responsavel_id: Number(f.responsavel_id) }),
      });
      setF(vazio);
      setMsg({ ok: true, text: "Aluno cadastrado." });
      alunos.reload();
    } catch (err) {
      setMsg({ ok: false, text: (err as Error).message });
    }
  }

  async function desativar(a: Aluno) {
    if (!window.confirm(`Desativar ${a.nome}?`)) return;
    try {
      await api(`/alunos/${a.id}`, { method: "DELETE" });
      alunos.reload();
    } catch (err) {
      setMsg({ ok: false, text: (err as Error).message });
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Alunos</h1>
      <form onSubmit={criar} className="card grid gap-3 md:grid-cols-2">
        <input className="input" placeholder="Nome" required value={f.nome} onChange={set("nome")} />
        <input className="input" type="date" required value={f.data_nascimento} onChange={set("data_nascimento")} />
        <input className="input" placeholder="Escola" required value={f.escola} onChange={set("escola")} />
        <input className="input" placeholder="Série" value={f.serie} onChange={set("serie")} />
        <select className="input md:col-span-2" required value={f.responsavel_id} onChange={set("responsavel_id")}>
          <option value="">Responsável…</option>
          {resp.data?.map((r) => (
            <option key={r.id} value={r.id}>{r.nome}</option>
          ))}
        </select>
        <button className="btn md:col-span-2">Cadastrar aluno</button>
        {msg &&
          (msg.ok ? <Success text={msg.text} /> : <p role="alert" className="text-red-700">{msg.text}</p>)}
      </form>
      {alunos.loading && <Loading />}
      {alunos.error && <ErrorBox message={alunos.error} onRetry={alunos.reload} />}
      {alunos.data && alunos.data.length === 0 && <Empty text="Nenhum aluno cadastrado." />}
      {alunos.data?.map((a) => (
        <div key={a.id} className="card flex items-center justify-between gap-3">
          <div>
            <p className="font-semibold">{a.nome}</p>
            <p className="text-sm text-slate-600">
              {a.escola}{a.serie ? ` · ${a.serie}` : ""} · nasc. {fmtData(a.data_nascimento)}
            </p>
            <p className="text-sm text-slate-500">Resp.: {nomeResp(a.responsavel_id)}</p>
          </div>
          <button className="btn-ghost" onClick={() => desativar(a)}>Desativar</button>
        </div>
      ))}
    </div>
  );
}
