"use client";
import { useState } from "react";
import { Empty, ErrorBox, Loading } from "@/components/StateViews";
import { api } from "@/lib/api";
import type { Aviso } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const dataHora = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });

export default function AvisosResponsavel() {
  const avisos = useApi<Aviso[]>("/responsavel/avisos");
  const [erro, setErro] = useState<string | null>(null);

  async function marcar(a: Aviso) {
    if (a.lida) return;
    setErro(null);
    try {
      await api(`/responsavel/avisos/${a.id}/lida`, { method: "POST" });
      avisos.reload();
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  async function marcarTodas() {
    setErro(null);
    try {
      await api("/responsavel/avisos/lidas", { method: "POST" });
      avisos.reload();
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  const naoLidas = avisos.data?.filter((a) => !a.lida).length ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h1 className="page-title">Avisos</h1>
        {naoLidas > 0 && (
          <button className="btn-ghost" onClick={marcarTodas}>
            Marcar todos como lidos
          </button>
        )}
      </div>
      {erro && (
        <p role="alert" className="text-red-700">
          {erro}
        </p>
      )}
      {avisos.loading && !avisos.data && <Loading />}
      {avisos.error && <ErrorBox message={avisos.error} onRetry={avisos.reload} />}
      {avisos.data && avisos.data.length === 0 && <Empty text="Nenhum aviso por enquanto." />}

      {avisos.data?.map((a) => (
        <button
          key={a.id}
          onClick={() => marcar(a)}
          className={`card block w-full space-y-1 text-left ${a.lida ? "" : "card-unread"}`}
        >
          <div className="flex items-start justify-between gap-2">
            <p className="font-semibold">
                            {a.titulo}
            </p>
            <span className="shrink-0 text-xs text-slate-500">{dataHora(a.created_at)}</span>
          </div>
          <p className="whitespace-pre-line">{a.mensagem}</p>
        </button>
      ))}
    </div>
  );
}