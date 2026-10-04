"use client";
import { Check, Play, Square, Undo2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import MapaFrota from "@/components/MapaFrota";
import { Empty, ErrorBox, Loading } from "@/components/StateViews";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { MotoristaRota, MotoristaRotaDetalhe, Presencas, StatusPresenca } from "@/lib/types";
import { useApi } from "@/lib/useApi";

function Detalhe({ id, posicao }: { id: number; posicao: { lat: number; lng: number } | null }) {
  const { data, error, loading, reload } = useApi<MotoristaRotaDetalhe>(`/motorista/rotas/${id}`);
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data) return null;

  const semParada = data.alunos.filter((a) => a.parada_id === null);
  return (
    <div className="space-y-3 border-t pt-3">
      <MapaFrota
        altura="h-64"
        paradas={data.paradas.map((p) => ({ lat: p.latitude, lng: p.longitude, nome: p.nome, ordem: p.ordem }))}
        vans={posicao ? [{ id, lat: posicao.lat, lng: posicao.lng, rotulo: "Você está aqui" }] : []}
        ajusteKey={id}
      />
      {data.paradas.length === 0 && <p className="text-slate-500">Esta rota ainda não tem paradas.</p>}
      {data.paradas.map((p) => {
        const alunos = data.alunos.filter((a) => a.parada_id === p.id);
        return (
          <div key={p.id}>
            <p className="font-medium">
              {p.ordem}. {p.nome}
            </p>
            {alunos.length === 0 ? (
              <p className="pl-4 text-sm text-slate-400">Nenhum aluno nesta parada</p>
            ) : (
              <ul className="pl-4 text-sm">
                {alunos.map((a) => (
                  <li key={a.aluno_id}>
                    {a.nome} <span className="text-slate-500">· {a.escola}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
      {semParada.length > 0 && (
        <div>
          <p className="font-medium text-slate-600">Sem parada definida</p>
          <ul className="pl-4 text-sm">
            {semParada.map((a) => (
              <li key={a.aluno_id}>
                {a.nome} <span className="text-slate-500">· {a.escola}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Chamada({ viagemId }: { viagemId: number }) {
  const caminho = `/motorista/viagens/${viagemId}/presencas`;
  const { data, error, loading, reload } = useApi<Presencas>(caminho);
  const [erro, setErro] = useState<string | null>(null);

  async function marcar(alunoId: number, status: StatusPresenca) {
    setErro(null);
    try {
      await api(`${caminho}/${alunoId}`, { method: "PUT", body: JSON.stringify({ status }) });
      reload();
    } catch (err) {
      setErro((err as Error).message);
    }
  }

  async function desfazer(alunoId: number) {
    setErro(null);
    try {
      await api(`${caminho}/${alunoId}`, { method: "DELETE" });
      reload();
    } catch (err) {
      setErro((err as Error).message);
    }
  }

  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center justify-between">
        <p className="font-semibold">Chamada</p>
        <p className="text-sm">
          {data.presentes} presentes · {data.faltas} faltas · {data.pendentes} pendentes
        </p>
      </div>
      {erro && (
        <p role="alert" className="text-red-700">
          {erro}
        </p>
      )}
      {data.alunos.length === 0 && <p className="text-slate-500">Nenhum aluno nesta rota.</p>}
      {data.alunos.map((a, i) => {
        const novaParada = i === 0 || data.alunos[i - 1].parada_id !== a.parada_id;
        return (
          <div key={a.aluno_id}>
            {novaParada && (
              <p className="mt-2 text-xs font-semibold uppercase text-slate-500">
                {a.parada_nome ?? "Sem parada"}
              </p>
            )}
            <div className="flex items-center justify-between gap-2 py-1">
              <p className="font-medium">{a.nome}</p>
              <div className="flex items-center gap-1">
                <button
                  className={`seg ${a.status === "PRESENTE" ? "seg-on-ok" : ""}`}
                  onClick={() => marcar(a.aluno_id, "PRESENTE")}
                >
                  <Check className="h-4 w-4" />
                  Presente
                </button>
                <button
                  className={`seg ${a.status === "FALTA" ? "seg-on-bad" : ""}`}
                  onClick={() => marcar(a.aluno_id, "FALTA")}
                >
                  <X className="h-4 w-4" />
                  Faltou
                </button>
                {a.status !== null && (
                  <button className="px-2 text-slate-500" aria-label="Desfazer" onClick={() => desfazer(a.aluno_id)}>
                    <Undo2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

type WakeLockLike = { request: (tipo: "screen") => Promise<{ release: () => Promise<void> }> };

function EnviarGps({
  viagemId,
  onPosicao,
}: {
  viagemId: number;
  onPosicao: (p: { lat: number; lng: number }) => void;
}) {
  const [estado, setEstado] = useState<"aguardando" | "enviando" | "negado" | "indisponivel" | "erro">("aguardando");
  const [ultimo, setUltimo] = useState<Date | null>(null);
  const ultimoEnvio = useRef(0);

  useEffect(() => {
    if (!("geolocation" in navigator)) {
      setEstado("indisponivel");
      return;
    }
    // Mantém a tela acesa: com a tela apagada o navegador para de informar a posição
    let wake: { release: () => Promise<void> } | null = null;
    const wl = (navigator as unknown as { wakeLock?: WakeLockLike }).wakeLock;
    wl?.request("screen")
      .then((w) => {
        wake = w;
      })
      .catch(() => {});

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const { latitude, longitude, speed, heading } = pos.coords;
        onPosicao({ lat: latitude, lng: longitude });
        const agora = Date.now();
        if (agora - ultimoEnvio.current < 5000) return; // no máximo 1 envio a cada 5 s
        ultimoEnvio.current = agora;
        api(`/motorista/viagens/${viagemId}/localizacao`, {
          method: "POST",
          body: JSON.stringify({
            latitude,
            longitude,
            velocidade: speed !== null && speed >= 0 ? speed : null,
            direcao: heading !== null && !Number.isNaN(heading) ? heading : null,
          }),
        })
          .then(() => {
            setEstado("enviando");
            setUltimo(new Date());
          })
          .catch(() => setEstado("erro"));
      },
      (err) => setEstado(err.code === err.PERMISSION_DENIED ? "negado" : "erro"),
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 },
    );
    return () => {
      navigator.geolocation.clearWatch(watchId);
      wake?.release().catch(() => {});
    };
  }, [viagemId, onPosicao]);

  const textos = {
    aguardando: "Obtendo sua localização…",
    enviando: `Localização sendo enviada${ultimo ? ` (${ultimo.toLocaleTimeString("pt-BR")})` : ""}`,
    negado: "Permissão de localização negada. Libere o acesso à localização no navegador.",
    indisponivel: "Este aparelho não oferece localização.",
    erro: "Falha ao enviar a localização. Tentando novamente…",
  } as const;

  return (
    <p
      className={`callout ${
        estado === "enviando" || estado === "aguardando" ? "callout-info" : "callout-warn"
      }`}
    >
      {textos[estado]}
    </p>
  );
}

export default function MotoristaHome() {
  const { user } = useAuth();
  const rotas = useApi<MotoristaRota[]>("/motorista/rotas");
  const [erro, setErro] = useState<string | null>(null);
  const [aberta, setAberta] = useState<number | null>(null);
  const [ocupado, setOcupado] = useState<number | null>(null);
  const [pos, setPos] = useState<{ lat: number; lng: number } | null>(null);

  async function executar(rotaId: number, caminho: string) {
    setErro(null);
    setOcupado(rotaId);
    try {
      await api(caminho, { method: "POST" });
      rotas.reload();
    } catch (err) {
      setErro((err as Error).message);
    } finally {
      setOcupado(null);
    }
  }

  const iniciar = (r: MotoristaRota) => executar(r.id, `/motorista/rotas/${r.id}/viagem/iniciar`);
  const encerrar = (r: MotoristaRota) => {
    if (!r.viagem_em_andamento_id) return;
    if (!confirm(`Encerrar a viagem "${r.nome}"?`)) return;
    executar(r.id, `/motorista/viagens/${r.viagem_em_andamento_id}/encerrar`);
  };

  return (
    <div className="space-y-4">
      <h1 className="page-title">Olá, {user?.nome.split(" ")[0]}</h1>
      <h2 className="font-semibold">Suas rotas</h2>

      {erro && (
        <p role="alert" className="callout callout-danger">
          {erro}
        </p>
      )}
      {rotas.loading && !rotas.data && <Loading />}
      {rotas.error && <ErrorBox message={rotas.error} onRetry={rotas.reload} />}
      {rotas.data && rotas.data.length === 0 && <Empty text="Nenhuma rota atribuída a você." />}

      {rotas.data?.map((r) => {
        const emViagem = r.viagem_em_andamento_id !== null;
        return (
          <div key={r.id} className={`card space-y-3 ${emViagem ? "card-live" : ""}`}>
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-lg font-semibold">{r.nome}</p>
                {r.escola && <p className="text-sm text-slate-500">{r.escola}</p>}
                <p className="text-sm">
                  {r.veiculo ? `${r.veiculo.apelido} · ${r.veiculo.placa}` : "Sem veículo"}
                </p>
                <p className="text-sm text-slate-500">
                  {r.total_paradas} paradas · {r.total_alunos} alunos
                </p>
              </div>
              {emViagem && (
                <span className="badge badge-ok">
                  Em viagem
                </span>
              )}
            </div>

            {emViagem ? (
              <button className="btn btn-danger w-full" disabled={ocupado === r.id} onClick={() => encerrar(r)}>
                <Square className="h-4 w-4" />
                Encerrar viagem
              </button>
            ) : (
              <button className="btn w-full" disabled={ocupado === r.id} onClick={() => iniciar(r)}>
                <Play className="h-4 w-4" />
                Iniciar viagem
              </button>
            )}

            {r.viagem_em_andamento_id !== null && (
              <>
                <EnviarGps viagemId={r.viagem_em_andamento_id} onPosicao={setPos} />
                <Chamada viagemId={r.viagem_em_andamento_id} />
              </>
            )}

            <button className="btn-ghost w-full" onClick={() => setAberta(aberta === r.id ? null : r.id)}>
              {aberta === r.id ? "Ocultar paradas e alunos" : "Ver paradas e alunos"}
            </button>
            {aberta === r.id && <Detalhe id={r.id} posicao={emViagem ? pos : null} />}
          </div>
        );
      })}
    </div>
  );
}