"use client";
import { ArrowLeft, Check, Clock, X } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect } from "react";
import MapaFrota from "@/components/MapaFrota";
import { Empty, ErrorBox, Loading } from "@/components/StateViews";
import type { Acompanhamento, PresencaHistorico, StatusPresenca } from "@/lib/types";
import { useApi } from "@/lib/useApi";
import { useViagensAoVivo } from "@/lib/useViagensAoVivo";

const dataHora = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });

function Chamada({ nome, status }: { nome: string; status: StatusPresenca | null }) {
  if (status === "PRESENTE")
    return (
      <p className="callout callout-ok flex items-center gap-2">
        <Check className="h-4 w-4 shrink-0" />
        {nome} está presente na viagem de agora.
      </p>
    );
  if (status === "FALTA")
    return (
      <p className="callout callout-danger flex items-center gap-2">
        <X className="h-4 w-4 shrink-0" />
        {nome} foi marcado como faltou nesta viagem.
      </p>
    );
  return (
    <p className="callout flex items-center gap-2">
      <Clock className="h-4 w-4 shrink-0" />
      A chamada desta viagem ainda não foi feita.
    </p>
  );
}

export default function FilhoPage() {
  const { id } = useParams<{ id: string }>();
  const ac = useApi<Acompanhamento>(`/responsavel/filhos/${id}/acompanhamento`);
  const hist = useApi<PresencaHistorico>(`/responsavel/filhos/${id}/presencas?dias=30`);
  const { viagens, conectado, carregando } = useViagensAoVivo("/responsavel/viagens/ativas");

  const recarregar = ac.reload;
  useEffect(() => {
    const t = setInterval(recarregar, 15000);
    return () => clearInterval(t);
  }, [recarregar]);

  if (ac.loading && !ac.data) return <Loading />;
  if (ac.error) return <ErrorBox message={ac.error} onRetry={ac.reload} />;
  if (!ac.data) return null;

  const nome = ac.data.aluno_nome;
  const primeiro = nome.split(" ")[0];

  return (
    <div className="space-y-4">
      <Link href="/responsavel" className="link inline-flex items-center gap-1 text-sm">
        <ArrowLeft className="h-4 w-4" />
        Voltar
      </Link>
      <div className="flex items-center justify-between gap-2">
        <h1 className="page-title">{nome}</h1>
        <span className={`badge gap-1.5 ${conectado ? "badge-ok" : "badge-neutral"}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${conectado ? "bg-emerald-500" : "bg-slate-400"}`} />
          {conectado ? "Ao vivo" : "Atualizando"}
        </span>
      </div>

      {ac.data.rotas.length === 0 && <Empty text="Este aluno ainda não está em nenhuma rota." />}

      {ac.data.rotas.map((r) => {
        const aoVivo = viagens.find((v) => v.rota_id === r.rota_id);
        const emViagem = carregando ? r.viagem !== null : aoVivo !== undefined;
        const pos = aoVivo?.posicao ?? r.viagem?.posicao ?? null;
        return (
          <section key={r.rota_id} className={`card space-y-3 ${emViagem ? "card-live" : ""}`}>
            <div>
              <p className="text-lg font-semibold">{r.rota_nome}</p>
              <dl className="mt-2 grid grid-cols-[auto,1fr] gap-x-4 gap-y-1 text-sm">
                <dt className="text-slate-500">Veículo</dt>
                <dd>
                  {r.veiculo_apelido
                    ? `${r.veiculo_apelido}${r.veiculo_placa ? ` · ${r.veiculo_placa}` : ""}`
                    : "A definir"}
                </dd>
                <dt className="text-slate-500">Motorista</dt>
                <dd>{r.motorista_nome ?? "A definir"}</dd>
                <dt className="text-slate-500">Parada de {primeiro}</dt>
                <dd>{r.parada_nome ?? "Não definida"}</dd>
              </dl>
            </div>

            {emViagem ? (
              <>
                <p className="flex items-center gap-2 text-sm font-medium text-emerald-700">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
                  Viagem em andamento
                </p>
                <Chamada nome={primeiro} status={r.viagem?.status_chamada ?? null} />
                {!pos && <p className="text-sm text-slate-500">Aguardando a primeira posição da van…</p>}
              </>
            ) : (
              <p className="text-sm text-slate-500">Nenhuma viagem em andamento agora.</p>
            )}

            {r.paradas.length > 0 || pos ? (
              <MapaFrota
                altura="h-72"
                paradas={r.paradas.map((p) => ({
                  lat: p.latitude,
                  lng: p.longitude,
                  nome: `${p.nome}${p.id === r.parada_id ? " (parada do aluno)" : ""}`,
                  ordem: p.ordem,
                }))}
                vans={
                  emViagem && pos
                    ? [
                        {
                          id: r.rota_id,
                          lat: pos.latitude,
                          lng: pos.longitude,
                          rotulo: `${r.rota_nome}${r.veiculo_apelido ? ` · ${r.veiculo_apelido}` : ""}`,
                          destaque: true,
                        },
                      ]
                    : []
                }
                ajusteKey={r.rota_id}
              />
            ) : null}
          </section>
        );
      })}

      <section className="card space-y-3">
        <h2 className="font-semibold">Presença nos últimos 30 dias</h2>
        {hist.loading && !hist.data && <Loading />}
        {hist.error && <ErrorBox message={hist.error} onRetry={hist.reload} />}
        {hist.data && (
          <>
            <p className="text-sm">
              {hist.data.presentes} presenças · {hist.data.faltas} faltas
            </p>
            {hist.data.registros.length === 0 && <p className="text-slate-500">Nenhum registro de presença neste período.</p>}
            <ul className="divide-y">
              {hist.data.registros.map((p) => (
                <li key={p.viagem_id} className="flex items-start justify-between gap-2 py-2">
                  <div>
                    <p className="font-medium">{dataHora(p.iniciada_em)}</p>
                    <p className="text-xs text-slate-500">
                      {p.rota_nome}
                      {p.observacao ? ` · ${p.observacao}` : ""}
                    </p>
                  </div>
                  <span
                    className={`badge ${
                      p.status === "PRESENTE" ? "badge-ok" : "badge-danger"
                    }`}
                  >
                    {p.status === "PRESENTE" ? "Presente" : "Faltou"}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </div>
  );
}