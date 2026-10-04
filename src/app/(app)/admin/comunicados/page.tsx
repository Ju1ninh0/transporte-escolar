"use client";
import { useState } from "react";
import { Success } from "@/components/StateViews";
import { api } from "@/lib/api";
import type { RotaResumo } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Msg = { ok: boolean; text: string } | null;

export default function ComunicadosPage() {
  const rotas = useApi<RotaResumo[]>("/rotas?status=ATIVA");
  const [f, setF] = useState({ titulo: "", mensagem: "", rota_id: "" });
  const [msg, setMsg] = useState<Msg>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    setEnviando(true);
    try {
      const r = await api<{ destinatarios: number }>("/comunicados", {
        method: "POST",
        body: JSON.stringify({
          titulo: f.titulo,
          mensagem: f.mensagem,
          rota_id: f.rota_id ? Number(f.rota_id) : null,
        }),
      });
      setF({ titulo: "", mensagem: "", rota_id: "" });
      setMsg({ ok: true, text: `Aviso enviado para ${r.destinatarios} ${r.destinatarios === 1 ? "responsável" : "responsáveis"}.` });
    } catch (err) {
      setMsg({ ok: false, text: (err as Error).message });
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="page-title">Avisos aos responsáveis</h1>
      <form onSubmit={enviar} className="card space-y-3">
        <select className="input" value={f.rota_id} onChange={(e) => setF({ ...f, rota_id: e.target.value })}>
          <option value="">Todos os responsáveis</option>
          {rotas.data?.map((r) => (
            <option key={r.id} value={r.id}>
              Somente a rota: {r.nome}
            </option>
          ))}
        </select>
        <input
          className="input"
          required
          maxLength={120}
          placeholder="Título (ex.: Van atrasada hoje)"
          value={f.titulo}
          onChange={(e) => setF({ ...f, titulo: e.target.value })}
        />
        <textarea
          className="input"
          required
          rows={5}
          maxLength={2000}
          placeholder="Mensagem"
          value={f.mensagem}
          onChange={(e) => setF({ ...f, mensagem: e.target.value })}
        />
        <button className="btn w-full" disabled={enviando}>
          {enviando ? "Enviando…" : "Enviar aviso"}
        </button>
        {msg && (msg.ok ? <Success text={msg.text} /> : <p role="alert" className="text-red-700">{msg.text}</p>)}
      </form>
      <p className="text-xs text-slate-500">O aviso aparece na tela “Avisos” de cada responsável.</p>
    </div>
  );
}