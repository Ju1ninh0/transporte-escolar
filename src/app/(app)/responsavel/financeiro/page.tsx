"use client";
import { useState } from "react";
import { Empty, ErrorBox, Loading } from "@/components/StateViews";
import { fmtData, type Mensalidade, type MensalidadeDetalhe, type PixInfo, type StatusMensalidade } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const brl = (v: string | number) => Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
const mesAno = (iso: string) => {
  const [y, m] = iso.split("-");
  return `${MESES[Number(m) - 1]}/${y}`;
};

const COR: Record<StatusMensalidade, string> = {
  PENDENTE: "badge-warn",
  PAGO: "badge-ok",
  ATRASADO: "badge-danger",
  CANCELADO: "badge-neutral",
};
const ROTULO: Record<StatusMensalidade, string> = {
  PENDENTE: "Pendente",
  PAGO: "Pago",
  ATRASADO: "Atrasada",
  CANCELADO: "Cancelada",
};

function Detalhe({ id }: { id: number }) {
  const { data, error, loading, reload } = useApi<MensalidadeDetalhe>(`/responsavel/mensalidades/${id}`);
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data) return null;
  return (
    <div className="space-y-1 border-t pt-2 text-sm">
      <p>
        Valor: {brl(data.valor)} · Pago: {brl(data.valor_pago)} · Saldo: <strong>{brl(data.saldo)}</strong>
      </p>
      {data.pagamentos.length === 0 ? (
        <p className="text-slate-500">Nenhum pagamento registrado.</p>
      ) : (
        <ul className="space-y-0.5">
          {data.pagamentos.map((p) => (
            <li key={p.id}>
              {brl(p.valor)} em {p.data_pagamento ? fmtData(p.data_pagamento) : "-"} ({p.metodo})
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function FinanceiroResponsavel() {
  const [filtro, setFiltro] = useState<"" | StatusMensalidade>("");
  const mensalidades = useApi<Mensalidade[]>(`/responsavel/mensalidades${filtro ? `?status=${filtro}` : ""}`);
  const pix = useApi<PixInfo | null>("/responsavel/pix");
  const [aberta, setAberta] = useState<number | null>(null);
  const [copiado, setCopiado] = useState(false);

  async function copiar(chave: string) {
    try {
      await navigator.clipboard.writeText(chave);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2500);
    } catch {
      window.prompt("Copie a chave PIX:", chave);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="page-title">Financeiro</h1>

      {pix.data && (
        <section className="card card-ok space-y-2">
          <h2 className="font-semibold">Como pagar (PIX)</h2>
          <p className="text-sm">
            Recebedor: <strong>{pix.data.recebedor}</strong>
          </p>
          <p className="break-all text-sm">
            Chave ({pix.data.tipo_chave}): <strong>{pix.data.chave}</strong>
          </p>
          {pix.data.mensagem && <p className="text-sm text-slate-600">{pix.data.mensagem}</p>}
          <button className="btn w-full" onClick={() => pix.data && copiar(pix.data.chave)}>
            {copiado ? "Chave copiada" : "Copiar chave PIX"}
          </button>
          <p className="text-xs text-slate-500">Depois de pagar, a confirmação é feita pela administração.</p>
        </section>
      )}

      <div className="card">
        <select className="input" value={filtro} onChange={(e) => setFiltro(e.target.value as "" | StatusMensalidade)}>
          <option value="">Todas as mensalidades</option>
          <option value="PENDENTE">Pendentes</option>
          <option value="ATRASADO">Atrasadas</option>
          <option value="PAGO">Pagas</option>
        </select>
      </div>

      {mensalidades.loading && !mensalidades.data && <Loading />}
      {mensalidades.error && <ErrorBox message={mensalidades.error} onRetry={mensalidades.reload} />}
      {mensalidades.data && mensalidades.data.length === 0 && <Empty text="Nenhuma mensalidade encontrada." />}

      {mensalidades.data?.map((m) => (
        <div key={m.id} className="card space-y-2">
          <button className="flex w-full items-start justify-between gap-2 text-left" onClick={() => setAberta(aberta === m.id ? null : m.id)}>
            <div>
              <p className="font-semibold">
                {mesAno(m.mes_referencia)} · {m.aluno_nome}
              </p>
              <p className="text-sm text-slate-600">
                {brl(m.valor)} · vence em {fmtData(m.vencimento)}
              </p>
              {m.status !== "PAGO" && m.status !== "CANCELADO" && (
                <p className="text-sm">
                  Saldo: <strong>{brl(m.saldo)}</strong>
                </p>
              )}
            </div>
            <span className={`badge ${COR[m.status]}`}>{ROTULO[m.status]}</span>
          </button>
          {aberta === m.id && <Detalhe id={m.id} />}
        </div>
      ))}
    </div>
  );
}