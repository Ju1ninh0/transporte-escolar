"use client";
import { useEffect, useState } from "react";
import MapaFrota from "@/components/MapaFrota";
import { Empty, ErrorBox, Loading } from "@/components/StateViews";
import { api } from "@/lib/api";
import type { Parada, PontoTrilha } from "@/lib/types";
import { useViagensAoVivo } from "@/lib/useViagensAoVivo";

function haQuanto(ts: string, agora: number) {
  const s = Math.max(0, Math.round((agora - Date.parse(ts)) / 1000));
  if (Number.isNaN(s)) return "";
  if (s < 60) return `há ${s} s`;
  if (s < 3600) return `há ${Math.floor(s / 60)} min`;
  return `há ${Math.floor(s / 3600)} h`;
}

export default function MapaAoVivoPage() {
  const { viagens, conectado, erro, carregando, recarregar } = useViagensAoVivo();
  const [sel, setSel] = useState<number | null>(null);
  const [paradas, setParadas] = useState<Parada[]>([]);
  const [trilha, setTrilha] = useState<PontoTrilha[]>([]);
  const [agora, setAgora] = useState(() => Date.now());

  useEffect(() => {
    const t = setInterval(() => setAgora(Date.now()), 5000);
    return () => clearInterval(t);
  }, []);

  const selecionada = viagens.find((v) => v.viagem_id === sel) ?? null;
  const viagemId = selecionada?.viagem_id ?? null;
  const rotaId = selecionada?.rota_id ?? null;

  // Paradas e trilha da viagem escolhida
  useEffect(() => {
    if (viagemId === null || rotaId === null) {
      setParadas([]);
      setTrilha([]);
      return;
    }
    let ativo = true;
    const carregar = () => {
      api<Parada[]>(`/rotas/${rotaId}/paradas`)
        .then((p) => ativo && setParadas(p))
        .catch(() => {});
      api<PontoTrilha[]>(`/viagens/${viagemId}/trilha?limite=300`)
        .then((t) => ativo && setTrilha(t))
        .catch(() => {});
    };
    carregar();
    const t = setInterval(carregar, 15000);
    return () => {
      ativo = false;
      clearInterval(t);
    };
  }, [viagemId, rotaId]);

  const vans = viagens
    .filter((v) => v.posicao)
    .map((v) => ({
      id: v.viagem_id,
      lat: v.posicao!.latitude,
      lng: v.posicao!.longitude,
      rotulo: `${v.rota_nome}${v.veiculo_apelido ? ` · ${v.veiculo_apelido}` : ""}`,
      destaque: v.viagem_id === sel,
    }));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h1 className="page-title">Vans ao vivo</h1>
        <span className={`badge gap-1.5 ${conectado ? "badge-ok" : "badge-warn"}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${conectado ? "bg-emerald-500" : "bg-amber-500"}`} />
          {conectado ? "Ao vivo" : "Reconectando…"}
        </span>
      </div>

      {erro && <ErrorBox message={erro} onRetry={recarregar} />}

      <MapaFrota
        altura="h-80 md:h-[28rem]"
        vans={vans}
        paradas={paradas.map((p) => ({ lat: p.latitude, lng: p.longitude, nome: p.nome, ordem: p.ordem }))}
        trilha={trilha.map((p) => ({ lat: p.latitude, lng: p.longitude }))}
        ajusteKey={sel ?? "todas"}
      />

      {carregando && viagens.length === 0 && <Loading />}
      {!carregando && viagens.length === 0 && <Empty text="Nenhuma viagem em andamento no momento." />}

      {viagens.map((v) => (
        <button
          key={v.viagem_id}
          onClick={() => setSel(sel === v.viagem_id ? null : v.viagem_id)}
          className={`card block w-full space-y-1 text-left ${v.viagem_id === sel ? "card-selected" : ""}`}
        >
          <p className="font-semibold">{v.rota_nome}</p>
          <p className="text-sm text-slate-600">
            {v.veiculo_apelido ?? "Sem veículo"}
            {v.veiculo_placa ? ` · ${v.veiculo_placa}` : ""} · Motorista: {v.motorista_nome ?? "não definido"}
          </p>
          <p className="text-sm text-slate-500">
            {v.posicao
              ? `Última posição ${haQuanto(v.posicao.timestamp, agora)}${
                  v.posicao.velocidade !== null ? ` · ${Math.round(v.posicao.velocidade * 3.6)} km/h` : ""
                }`
              : "Aguardando a primeira posição do motorista"}
          </p>
        </button>
      ))}
      {viagens.length > 0 && (
        <p className="text-xs text-slate-500">Toque em uma viagem para ver as paradas e o trajeto percorrido.</p>
      )}
    </div>
  );
}