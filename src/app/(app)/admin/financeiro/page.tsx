"use client";

import { useState } from "react";

import { Empty, ErrorBox, Loading } from "@/components/StateViews";
import { api } from "@/lib/api";
import type {
  MetodoPagamento,
  Mensalidade,
  MensalidadeDetalhe,
  ResumoFinanceiro,
  StatusMensalidade,
} from "@/lib/types";
import { useApi } from "@/lib/useApi";

type AlunoOpcao = { id: number; nome: string };

const MESES = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

const brl = (v: string | number) =>
  Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function dataBR(iso: string | null): string {
  if (!iso) return "-";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

function mesBR(iso: string): string {
  const [y, m] = iso.split("-");
  return `${MESES[Number(m) - 1]}/${y}`;
}

function hojeISO(): string {
  const d = new Date();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mm}-${dd}`;
}

const STATUS_LABEL: Record<StatusMensalidade, string> = {
  PENDENTE: "Pendente",
  PAGO: "Pago",
  ATRASADO: "Atrasado",
  CANCELADO: "Cancelado",
};

const STATUS_COR: Record<StatusMensalidade, string> = {
  PENDENTE: "bg-amber-100 text-amber-700",
  PAGO: "bg-emerald-100 text-emerald-700",
  ATRASADO: "bg-red-100 text-red-700",
  CANCELADO: "bg-slate-200 text-slate-600",
};

const METODOS: { valor: MetodoPagamento; label: string }[] = [
  { valor: "PIX", label: "PIX" },
  { valor: "DINHEIRO", label: "Dinheiro" },
  { valor: "TRANSFERENCIA", label: "Transferência" },
  { valor: "OUTRO", label: "Outro" },
];

const campo = "w-full rounded-lg border border-slate-300 px-3 py-2";
const btnPrimario =
  "rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50";
const btnLink = "text-sm font-medium text-slate-700 underline";

function Selo({ status }: { status: StatusMensalidade }) {
  return (
    <span className={`rounded-full px-2 py-1 text-xs font-medium ${STATUS_COR[status]}`}>
      {STATUS_LABEL[status]}
    </span>
  );
}

function podePagar(m: Mensalidade): boolean {
  return m.status !== "CANCELADO" && Number(m.saldo) > 0;
}

function Modal({
  titulo,
  onClose,
  children,
}: {
  titulo: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center sm:p-4">
      <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-t-2xl bg-white p-5 sm:rounded-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{titulo}</h2>
          <button onClick={onClose} aria-label="Fechar" className="text-slate-500">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function NovaMensalidade({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const alunos = useApi<AlunoOpcao[]>("/alunos");
  const [f, setF] = useState({
    aluno_id: "",
    mes_referencia: hojeISO().slice(0, 7),
    vencimento: "",
    valor: "",
  });
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setSalvando(true);
    try {
      await api("/financeiro/mensalidades", {
        method: "POST",
        body: JSON.stringify({
          aluno_id: Number(f.aluno_id),
          mes_referencia: f.mes_referencia,
          vencimento: f.vencimento,
          valor: f.valor,
        }),
      });
      onSaved();
    } catch (err) {
      setErro((err as Error).message);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Modal titulo="Nova mensalidade" onClose={onClose}>
      <form onSubmit={salvar} className="space-y-3">
        <label className="block text-sm">
          Aluno
          <select
            required
            className={campo}
            value={f.aluno_id}
            onChange={(e) => setF({ ...f, aluno_id: e.target.value })}
          >
            <option value="">Selecione o aluno</option>
            {alunos.data?.map((a) => (
              <option key={a.id} value={a.id}>
                {a.nome}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          Mês de referência
          <input
            required
            type="month"
            className={campo}
            value={f.mes_referencia}
            onChange={(e) => setF({ ...f, mes_referencia: e.target.value })}
          />
        </label>
        <label className="block text-sm">
          Vencimento
          <input
            required
            type="date"
            className={campo}
            value={f.vencimento}
            onChange={(e) => setF({ ...f, vencimento: e.target.value })}
          />
        </label>
        <label className="block text-sm">
          Valor (R$)
          <input
            required
            type="number"
            step="0.01"
            min="0.01"
            className={campo}
            value={f.valor}
            onChange={(e) => setF({ ...f, valor: e.target.value })}
          />
        </label>
        {erro && <p className="text-sm text-red-600">{erro}</p>}
        <button className={`${btnPrimario} w-full`} disabled={salvando}>
          {salvando ? "Salvando..." : "Cadastrar"}
        </button>
      </form>
    </Modal>
  );
}

function RegistrarPagamento({
  m,
  onClose,
  onSaved,
}: {
  m: Mensalidade;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [f, setF] = useState({
    valor: m.saldo,
    data_pagamento: hojeISO(),
    metodo: "PIX" as MetodoPagamento,
    comprovante: "",
    provider_ref: "",
  });
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setSalvando(true);
    try {
      await api(`/financeiro/mensalidades/${m.id}/pagamentos`, {
        method: "POST",
        body: JSON.stringify({
          valor: f.valor,
          data_pagamento: f.data_pagamento,
          metodo: f.metodo,
          comprovante: f.comprovante || null,
          provider_ref: f.provider_ref || null,
        }),
      });
      onSaved();
    } catch (err) {
      setErro((err as Error).message);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Modal titulo={`Pagamento - ${m.aluno_nome}`} onClose={onClose}>
      <div className="mb-3 space-y-1 rounded-lg bg-slate-50 p-3 text-sm">
        <p>Valor da mensalidade: <b>{brl(m.valor)}</b></p>
        <p>Total pago: <b>{brl(m.valor_pago)}</b></p>
        <p>Saldo: <b>{brl(m.saldo)}</b></p>
      </div>
      <form onSubmit={salvar} className="space-y-3">
        <label className="block text-sm">
          Valor (R$)
          <input
            required
            type="number"
            step="0.01"
            min="0.01"
            max={m.saldo}
            className={campo}
            value={f.valor}
            onChange={(e) => setF({ ...f, valor: e.target.value })}
          />
        </label>
        <label className="block text-sm">
          Data
          <input
            required
            type="date"
            className={campo}
            value={f.data_pagamento}
            onChange={(e) => setF({ ...f, data_pagamento: e.target.value })}
          />
        </label>
        <label className="block text-sm">
          Método
          <select
            className={campo}
            value={f.metodo}
            onChange={(e) => setF({ ...f, metodo: e.target.value as MetodoPagamento })}
          >
            {METODOS.map((o) => (
              <option key={o.valor} value={o.valor}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          Comprovante (opcional)
          <input
            className={campo}
            value={f.comprovante}
            onChange={(e) => setF({ ...f, comprovante: e.target.value })}
          />
        </label>
        <label className="block text-sm">
          Referência do provedor (opcional)
          <input
            className={campo}
            value={f.provider_ref}
            onChange={(e) => setF({ ...f, provider_ref: e.target.value })}
          />
        </label>
        {erro && <p className="text-sm text-red-600">{erro}</p>}
        <button className={`${btnPrimario} w-full`} disabled={salvando}>
          {salvando ? "Registrando..." : "Registrar pagamento"}
        </button>
      </form>
    </Modal>
  );
}

function Detalhe({
  id,
  onClose,
  onPagar,
}: {
  id: number;
  onClose: () => void;
  onPagar: (m: Mensalidade) => void;
}) {
  const { data, error, loading, reload } = useApi<MensalidadeDetalhe>(
    `/financeiro/mensalidades/${id}`,
  );
  return (
    <Modal titulo="Mensalidade" onClose={onClose}>
      {loading && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data && (
        <div className="space-y-4">
          <div className="space-y-1 text-sm">
            <p><b>Aluno:</b> {data.aluno_nome}</p>
            <p><b>Responsável:</b> {data.responsavel_nome}</p>
            <p><b>Mês de referência:</b> {mesBR(data.mes_referencia)}</p>
            <p><b>Valor:</b> {brl(data.valor)}</p>
            <p><b>Valor pago:</b> {brl(data.valor_pago)}</p>
            <p><b>Saldo:</b> {brl(data.saldo)}</p>
            <p><b>Vencimento:</b> {dataBR(data.vencimento)}</p>
            <p className="flex items-center gap-2"><b>Status:</b> <Selo status={data.status} /></p>
          </div>
          <div>
            <h3 className="mb-2 font-semibold">Histórico de pagamentos</h3>
            {data.pagamentos.length === 0 && (
              <p className="text-sm text-slate-500">Nenhum pagamento registrado.</p>
            )}
            {data.pagamentos.map((p) => (
              <div key={p.id} className="border-t py-2 text-sm">
                <p>{dataBR(p.data_pagamento)} · {p.metodo}</p>
                <p className="font-medium">{brl(p.valor)}</p>
                {p.comprovante && <p className="text-slate-500">Comprovante: {p.comprovante}</p>}
              </div>
            ))}
          </div>
          {podePagar(data) && (
            <button className={`${btnPrimario} w-full`} onClick={() => onPagar(data)}>
              Registrar pagamento
            </button>
          )}
        </div>
      )}
    </Modal>
  );
}

function CardResumo({ titulo, valor }: { titulo: string; valor: string | undefined }) {
  return (
    <div className="card">
      <p className="text-sm text-slate-500">{titulo}</p>
      <p className="text-xl font-semibold">{brl(valor ?? "0")}</p>
    </div>
  );
}

export default function FinanceiroPage() {
  const [filtro, setFiltro] = useState<"" | StatusMensalidade>("");
  const [novaAberta, setNovaAberta] = useState(false);
  const [pagando, setPagando] = useState<Mensalidade | null>(null);
  const [detalheId, setDetalheId] = useState<number | null>(null);
  const [versao, setVersao] = useState(0);

  const resumo = useApi<ResumoFinanceiro>("/financeiro/resumo");
  const lista = useApi<Mensalidade[]>(
    `/financeiro/mensalidades${filtro ? `?status=${filtro}` : ""}`,
  );

  function recarregar() {
    resumo.reload();
    lista.reload();
    setVersao((v) => v + 1);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Financeiro</h1>
          <p className="text-slate-500">Mensalidades e pagamentos.</p>
        </div>
        <button className={btnPrimario} onClick={() => setNovaAberta(true)}>
          Nova mensalidade
        </button>
      </div>

      {resumo.error && <ErrorBox message={resumo.error} onRetry={resumo.reload} />}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <CardResumo titulo="Total previsto" valor={resumo.data?.total_previsto} />
        <CardResumo titulo="Recebido" valor={resumo.data?.total_recebido} />
        <CardResumo titulo="Pendente" valor={resumo.data?.total_pendente} />
        <CardResumo titulo="Atrasado" valor={resumo.data?.total_atrasado} />
      </div>
      <p className="text-xs text-slate-500">Os totais consideram o mês atual.</p>

      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Mensalidades</h2>
        <select
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={filtro}
          onChange={(e) => setFiltro(e.target.value as "" | StatusMensalidade)}
        >
          <option value="">Todos os status</option>
          {(Object.keys(STATUS_LABEL) as StatusMensalidade[]).map((s) => (
            <option key={s} value={s}>
              {STATUS_LABEL[s]}
            </option>
          ))}
        </select>
      </div>

      {lista.loading && <Loading />}
      {lista.error && <ErrorBox message={lista.error} onRetry={lista.reload} />}
      {lista.data && lista.data.length === 0 && <Empty text="Nenhuma mensalidade encontrada." />}

      {lista.data && lista.data.length > 0 && (
        <>
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full text-left text-sm">
              <thead className="border-b text-slate-500">
                <tr>
                  <th className="py-2">Aluno</th>
                  <th>Mês</th>
                  <th>Valor</th>
                  <th>Pago</th>
                  <th>Saldo</th>
                  <th>Vencimento</th>
                  <th>Status</th>
                  <th>Ação</th>
                </tr>
              </thead>
              <tbody>
                {lista.data.map((m) => (
                  <tr key={m.id} className="border-b">
                    <td className="py-2">
                      <button className={btnLink} onClick={() => setDetalheId(m.id)}>
                        {m.aluno_nome}
                      </button>
                    </td>
                    <td>{mesBR(m.mes_referencia)}</td>
                    <td>{brl(m.valor)}</td>
                    <td>{brl(m.valor_pago)}</td>
                    <td>{brl(m.saldo)}</td>
                    <td>{dataBR(m.vencimento)}</td>
                    <td><Selo status={m.status} /></td>
                    <td>
                      {podePagar(m) && (
                        <button className={btnLink} onClick={() => setPagando(m)}>
                          Registrar pagamento
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid gap-3 md:hidden">
            {lista.data.map((m) => (
              <div key={m.id} className="card">
                <div className="flex items-start justify-between gap-3">
                  <button className="text-left text-lg font-semibold" onClick={() => setDetalheId(m.id)}>
                    {m.aluno_nome}
                  </button>
                  <Selo status={m.status} />
                </div>
                <p className="text-sm text-slate-500">
                  {mesBR(m.mes_referencia)} · vence {dataBR(m.vencimento)}
                </p>
                <p className="mt-1 text-sm">
                  Valor {brl(m.valor)} · Pago {brl(m.valor_pago)} · Saldo <b>{brl(m.saldo)}</b>
                </p>
                {podePagar(m) && (
                  <button className={`${btnLink} mt-2`} onClick={() => setPagando(m)}>
                    Registrar pagamento
                  </button>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {novaAberta && (
        <NovaMensalidade
          onClose={() => setNovaAberta(false)}
          onSaved={() => {
            setNovaAberta(false);
            recarregar();
          }}
        />
      )}
      {detalheId !== null && (
        <Detalhe
          key={`${detalheId}-${versao}`}
          id={detalheId}
          onClose={() => setDetalheId(null)}
          onPagar={(m) => setPagando(m)}
        />
      )}
      {pagando && (
        <RegistrarPagamento
          m={pagando}
          onClose={() => setPagando(null)}
          onSaved={() => {
            setPagando(null);
            recarregar();
          }}
        />
      )}
    </div>
  );
}