"use client";
import Link from "next/link";
import { useEffect } from "react";
import { ErrorBox, Loading } from "@/components/StateViews";
import { fmtData, GRAVIDADES, type Gravidade, type ViagemAtiva } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Dashboard = {
  alunos_ativos: number;
  responsaveis: number;
  motoristas: number;
  veiculos_ativos: number;
  rotas_ativas: number;
  viagens_em_andamento: number;
  ocorrencias_30_dias: number;
  ocorrencias_recentes: { id: number; aluno_nome: string; tipo_nome: string; data: string; gravidade: Gravidade }[];
};

type ResumoFin = { total_previsto: string; total_recebido: string; total_pendente: string; total_atrasado: string };

const brl = (v: string | number) => Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const COR_GRAVIDADE: Record<Gravidade, string> = { LEVE: "badge-neutral", MEDIA: "badge-warn", GRAVE: "badge-danger" };

const ATALHOS = [
  { href: "/admin/alunos", titulo: "Cadastrar aluno", texto: "Novo aluno e responsável" },
  { href: "/admin/rotas", titulo: "Montar rota", texto: "Paradas, van e motorista" },
  { href: "/admin/comunicados", titulo: "Enviar aviso", texto: "Fale com os responsáveis" },
  { href: "/admin/ocorrencias", titulo: "Registrar ocorrência", texto: "Com sugestão de consequência" },
  { href: "/admin/financeiro", titulo: "Mensalidades", texto: "Lançar e dar baixa" },
  { href: "/admin/configuracoes", titulo: "Configurações", texto: "PIX e aviso de proximidade" },
];

function Numero({ rotulo, valor, href }: { rotulo: string; valor: number; href: string }) {
  return (
    <Link href={href} className="card block transition hover:bg-slate-50">
      <p className="text-sm text-slate-500">{rotulo}</p>
      <p className="mt-1 text-2xl font-semibold tracking-tight">{valor}</p>
    </Link>
  );
}

export default function PainelPage() {
  const painel = useApi<Dashboard>("/dashboard");
  const fin = useApi<ResumoFin>("/financeiro/resumo");
  const viagens = useApi<ViagemAtiva[]>("/viagens/ativas");

  const recarregarViagens = viagens.reload;
  const recarregarPainel = painel.reload;
  useEffect(() => {
    const t = setInterval(() => {
      recarregarViagens();
      recarregarPainel();
    }, 15000);
    return () => clearInterval(t);
  }, [recarregarViagens, recarregarPainel]);

  const hoje = new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" });
  const previsto = Number(fin.data?.total_previsto ?? 0);
  const recebido = Number(fin.data?.total_recebido ?? 0);
  const pct = previsto > 0 ? Math.min(100, Math.round((recebido / previsto) * 100)) : 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="page-title">Painel</h1>
        <p className="mt-1 text-sm capitalize text-slate-500">{hoje}</p>
      </div>

      {painel.loading && !painel.data && <Loading />}
      {painel.error && <ErrorBox message={painel.error} onRetry={painel.reload} />}

      {painel.data && (
        <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Numero rotulo="Alunos ativos" valor={painel.data.alunos_ativos} href="/admin/alunos" />
          <Numero rotulo="Rotas ativas" valor={painel.data.rotas_ativas} href="/admin/rotas" />
          <Numero rotulo="Veículos ativos" valor={painel.data.veiculos_ativos} href="/admin/veiculos" />
          <Numero rotulo="Viagens agora" valor={painel.data.viagens_em_andamento} href="/admin/mapa" />
        </section>
      )}

      <section className="space-y-3">
        <div className="flex items-baseline justify-between">
          <h2 className="font-semibold">Financeiro do mês</h2>
          <Link href="/admin/financeiro" className="link text-sm">
            Ver mensalidades
          </Link>
        </div>
        {fin.loading && !fin.data && <Loading />}
        {fin.error && <ErrorBox message={fin.error} onRetry={fin.reload} />}
        {fin.data && (
          <div className="card space-y-4">
            <div>
              <div className="flex items-baseline justify-between text-sm">
                <span className="text-slate-500">Recebido de {brl(previsto)} previstos</span>
                <span className="font-medium">{pct}%</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-slate-900 transition-all" style={{ width: `${pct}%` }} />
              </div>
            </div>
            <dl className="grid grid-cols-3 gap-3 text-sm">
              <div>
                <dt className="text-slate-500">Recebido</dt>
                <dd className="mt-0.5 font-semibold">{brl(fin.data.total_recebido)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">A vencer</dt>
                <dd className="mt-0.5 font-semibold">{brl(fin.data.total_pendente)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Atrasado</dt>
                <dd className={`mt-0.5 font-semibold ${Number(fin.data.total_atrasado) > 0 ? "text-red-700" : ""}`}>
                  {brl(fin.data.total_atrasado)}
                </dd>
              </div>
            </dl>
          </div>
        )}
      </section>

      <section className="space-y-3">
        <div className="flex items-baseline justify-between">
          <h2 className="font-semibold">Viagens em andamento</h2>
          <Link href="/admin/mapa" className="link text-sm">
            Abrir mapa
          </Link>
        </div>
        {viagens.data && viagens.data.length === 0 && (
          <p className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-6 text-center text-sm text-slate-500">
            Nenhuma viagem em andamento agora.
          </p>
        )}
        <div className="space-y-2">
          {viagens.data?.map((v) => (
            <div key={v.viagem_id} className="card flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate font-medium">{v.rota_nome}</p>
                <p className="truncate text-sm text-slate-500">
                  {v.veiculo_apelido ?? "Sem veículo"} · {v.motorista_nome ?? "Sem motorista"}
                </p>
              </div>
              <span className={`badge gap-1.5 ${v.posicao ? "badge-ok" : "badge-neutral"}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${v.posicao ? "bg-emerald-500" : "bg-slate-400"}`} />
                {v.posicao ? "Transmitindo" : "Sem sinal"}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-baseline justify-between">
          <h2 className="font-semibold">Ocorrências recentes</h2>
          <Link href="/admin/ocorrencias" className="link text-sm">
            Ver todas
          </Link>
        </div>
        {painel.data && painel.data.ocorrencias_recentes.length === 0 && (
          <p className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-6 text-center text-sm text-slate-500">
            Nenhuma ocorrência registrada.
          </p>
        )}
        {painel.data && painel.data.ocorrencias_recentes.length > 0 && (
          <div className="card divide-y divide-slate-100 p-0">
            {painel.data.ocorrencias_recentes.map((o) => (
              <div key={o.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <div className="min-w-0">
                  <p className="truncate font-medium">{o.aluno_nome}</p>
                  <p className="truncate text-sm text-slate-500">
                    {o.tipo_nome} · {fmtData(o.data)}
                  </p>
                </div>
                <span className={`badge ${COR_GRAVIDADE[o.gravidade]}`}>{GRAVIDADES.find((g) => g.value === o.gravidade)?.label}</span>
              </div>
            ))}
          </div>
        )}
        {painel.data && (
          <p className="text-xs text-slate-500">{painel.data.ocorrencias_30_dias} ocorrência(s) nos últimos 30 dias.</p>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="font-semibold">Atalhos</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {ATALHOS.map((a) => (
            <Link key={a.href} href={a.href} className="card block transition hover:bg-slate-50">
              <p className="font-medium">{a.titulo}</p>
              <p className="mt-0.5 text-sm text-slate-500">{a.texto}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}