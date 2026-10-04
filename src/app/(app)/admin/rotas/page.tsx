"use client";
import Link from "next/link";
import { useState } from "react";
import { Empty, ErrorBox, Loading, Success } from "@/components/StateViews";
import { api } from "@/lib/api";
import type { Motorista, RotaResumo, Veiculo } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Msg = { ok: boolean; text: string } | null;
const vazio = { nome: "", escola: "", veiculo_id: "", motorista_id: "" };

export default function RotasPage() {
  const [filtro, setFiltro] = useState("");
  const rotas = useApi<RotaResumo[]>(`/rotas${filtro ? `?status=${filtro}` : ""}`);
  const veiculos = useApi<Veiculo[]>("/veiculos?ativo=true");
  const motoristas = useApi<Motorista[]>("/motoristas");
  const [f, setF] = useState(vazio);
  const [msg, setMsg] = useState<Msg>(null);

  async function criar(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      await api("/rotas", {
        method: "POST",
        body: JSON.stringify({
          nome: f.nome,
          escola: f.escola.trim() || null,
          veiculo_id: f.veiculo_id ? Number(f.veiculo_id) : null,
          motorista_id: f.motorista_id ? Number(f.motorista_id) : null,
        }),
      });
      setF(vazio);
      setMsg({ ok: true, text: "Rota criada." });
      rotas.reload();
    } catch (err) {
      setMsg({ ok: false, text: (err as Error).message });
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="page-title">Rotas</h1>

      <form onSubmit={criar} className="card grid gap-3 md:grid-cols-2">
        <h2 className="font-semibold md:col-span-2">Nova rota</h2>
        <input
          className="input"
          required
          maxLength={120}
          placeholder="Nome (ex.: Rota Manhã)"
          value={f.nome}
          onChange={(e) => setF({ ...f, nome: e.target.value })}
        />
        <input
          className="input"
          maxLength={120}
          placeholder="Escola (opcional)"
          value={f.escola}
          onChange={(e) => setF({ ...f, escola: e.target.value })}
        />
        <select className="input" value={f.veiculo_id} onChange={(e) => setF({ ...f, veiculo_id: e.target.value })}>
          <option value="">Sem veículo</option>
          {veiculos.data?.map((v) => (
            <option key={v.id} value={v.id}>
              {v.apelido} · {v.placa}
            </option>
          ))}
        </select>
        <select
          className="input"
          value={f.motorista_id}
          onChange={(e) => setF({ ...f, motorista_id: e.target.value })}
        >
          <option value="">Sem motorista</option>
          {motoristas.data?.map((m) => (
            <option key={m.id} value={m.id}>
              {m.nome}
            </option>
          ))}
        </select>
        <button className="btn md:col-span-2">Criar rota</button>
        {msg && (msg.ok ? <Success text={msg.text} /> : <p role="alert" className="text-red-700 md:col-span-2">{msg.text}</p>)}
      </form>

      <div className="card">
        <select className="input" value={filtro} onChange={(e) => setFiltro(e.target.value)}>
          <option value="">Todas as rotas</option>
          <option value="ATIVA">Somente ativas</option>
          <option value="INATIVA">Somente inativas</option>
        </select>
      </div>

      {rotas.loading && !rotas.data && <Loading />}
      {rotas.error && <ErrorBox message={rotas.error} onRetry={rotas.reload} />}
      {rotas.data && rotas.data.length === 0 && <Empty text="Nenhuma rota encontrada." />}

      {rotas.data?.map((r) => (
        <Link key={r.id} href={`/admin/rotas/${r.id}`} className="card block space-y-1 active:bg-slate-50">
          <div className="flex items-center justify-between gap-2">
            <p className="font-semibold">{r.nome}</p>
            <span
              className={`badge ${
                r.status === "ATIVA" ? "badge-ok" : "badge-neutral"
              }`}
            >
              {r.status === "ATIVA" ? "Ativa" : "Inativa"}
            </span>
          </div>
          {r.escola && <p className="text-sm text-slate-500">{r.escola}</p>}
          <p className="text-sm text-slate-600">
            {r.veiculo ? `${r.veiculo.apelido} · ${r.veiculo.placa}` : "Sem veículo"} ·{" "}
            {r.motorista ? r.motorista.nome : "Sem motorista"}
          </p>
          <p className="text-sm text-slate-500">
            {r.total_paradas} paradas · {r.total_alunos} alunos
          </p>
        </Link>
      ))}
    </div>
  );
}