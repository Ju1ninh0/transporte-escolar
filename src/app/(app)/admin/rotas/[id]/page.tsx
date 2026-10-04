"use client";
import { ArrowLeft, ChevronDown, ChevronUp } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import MapaFrota from "@/components/MapaFrota";
import { ErrorBox, Loading, Success } from "@/components/StateViews";
import { api } from "@/lib/api";
import type { Aluno, Motorista, Parada, RotaDetalhe, StatusRota, Veiculo } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Msg = { ok: boolean; text: string } | null;

export default function RotaDetalhePage() {
  const { id } = useParams<{ id: string }>();
  const base = `/rotas/${id}`;
  const rota = useApi<RotaDetalhe>(base);
  const veiculos = useApi<Veiculo[]>("/veiculos");
  const motoristas = useApi<Motorista[]>("/motoristas");
  const alunos = useApi<Aluno[]>("/alunos");

  const [dados, setDados] = useState({ nome: "", escola: "", veiculo_id: "", motorista_id: "", status: "ATIVA" as StatusRota });
  const [msgDados, setMsgDados] = useState<Msg>(null);
  const [erro, setErro] = useState<string | null>(null);

  const [np, setNp] = useState({ nome: "", latitude: "", longitude: "" });
  const [editP, setEditP] = useState<{ id: number; nome: string; latitude: string; longitude: string } | null>(null);
  const [alunoSel, setAlunoSel] = useState("");
  const [paradaSel, setParadaSel] = useState("");

  useEffect(() => {
    if (!rota.data) return;
    setDados({
      nome: rota.data.nome,
      escola: rota.data.escola ?? "",
      veiculo_id: rota.data.veiculo ? String(rota.data.veiculo.id) : "",
      motorista_id: rota.data.motorista ? String(rota.data.motorista.id) : "",
      status: rota.data.status,
    });
  }, [rota.data]);

  async function acao(fn: () => Promise<unknown>, depois?: () => void) {
    setErro(null);
    try {
      await fn();
      depois?.();
      rota.reload();
    } catch (err) {
      setErro((err as Error).message);
    }
  }

  async function salvarDados(e: React.FormEvent) {
    e.preventDefault();
    setMsgDados(null);
    try {
      await api(base, {
        method: "PATCH",
        body: JSON.stringify({
          nome: dados.nome,
          escola: dados.escola.trim() || null,
          veiculo_id: dados.veiculo_id ? Number(dados.veiculo_id) : null,
          motorista_id: dados.motorista_id ? Number(dados.motorista_id) : null,
          status: dados.status,
        }),
      });
      setMsgDados({ ok: true, text: "Rota atualizada." });
      rota.reload();
    } catch (err) {
      setMsgDados({ ok: false, text: (err as Error).message });
    }
  }

  const adicionarParada = (e: React.FormEvent) => {
    e.preventDefault();
    acao(
      () =>
        api(`${base}/paradas`, {
          method: "POST",
          body: JSON.stringify({
            nome: np.nome,
            latitude: Number(np.latitude.replace(",", ".")),
            longitude: Number(np.longitude.replace(",", ".")),
          }),
        }),
      () => setNp({ nome: "", latitude: "", longitude: "" }),
    );
  };

  const salvarParada = () => {
    if (!editP) return;
    acao(
      () =>
        api(`${base}/paradas/${editP.id}`, {
          method: "PATCH",
          body: JSON.stringify({
            nome: editP.nome,
            latitude: Number(editP.latitude.replace(",", ".")),
            longitude: Number(editP.longitude.replace(",", ".")),
          }),
        }),
      () => setEditP(null),
    );
  };

  function mover(paradas: Parada[], indice: number, delta: -1 | 1) {
    const ids = paradas.map((p) => p.id);
    const alvo = indice + delta;
    if (alvo < 0 || alvo >= ids.length) return;
    [ids[indice], ids[alvo]] = [ids[alvo], ids[indice]];
    acao(() => api(`${base}/paradas/ordem`, { method: "PUT", body: JSON.stringify({ ids }) }));
  }

  const vincular = (e: React.FormEvent) => {
    e.preventDefault();
    acao(
      () =>
        api(`${base}/alunos`, {
          method: "POST",
          body: JSON.stringify({
            aluno_id: Number(alunoSel),
            parada_id: paradaSel ? Number(paradaSel) : null,
          }),
        }),
      () => {
        setAlunoSel("");
        setParadaSel("");
      },
    );
  };

  if (rota.loading && !rota.data) return <Loading />;
  if (rota.error) return <ErrorBox message={rota.error} onRetry={rota.reload} />;
  if (!rota.data) return null;

  const r = rota.data;
  const veiculoAtual = veiculos.data?.find((v) => v.id === r.veiculo?.id);
  const noRota = new Set(r.alunos.map((a) => a.aluno_id));
  const disponiveis = alunos.data?.filter((a) => a.ativo && !noRota.has(a.id)) ?? [];

  return (
    <div className="space-y-4">
      <Link href="/admin/rotas" className="link inline-flex items-center gap-1 text-sm">
        <ArrowLeft className="h-4 w-4" />
        Voltar para rotas
      </Link>
      <h1 className="page-title">{r.nome}</h1>
      {erro && (
        <p role="alert" className="callout callout-danger">
          {erro}
        </p>
      )}

      {/* Dados da rota */}
      <form onSubmit={salvarDados} className="card grid gap-3 md:grid-cols-2">
        <h2 className="font-semibold md:col-span-2">Dados da rota</h2>
        <input
          className="input"
          required
          maxLength={120}
          value={dados.nome}
          onChange={(e) => setDados({ ...dados, nome: e.target.value })}
        />
        <input
          className="input"
          maxLength={120}
          placeholder="Escola"
          value={dados.escola}
          onChange={(e) => setDados({ ...dados, escola: e.target.value })}
        />
        <select
          className="input"
          value={dados.veiculo_id}
          onChange={(e) => setDados({ ...dados, veiculo_id: e.target.value })}
        >
          <option value="">Sem veículo</option>
          {veiculos.data
            ?.filter((v) => v.ativo || v.id === r.veiculo?.id)
            .map((v) => (
              <option key={v.id} value={v.id}>
                {v.apelido} · {v.placa} ({v.capacidade} lugares)
              </option>
            ))}
        </select>
        <select
          className="input"
          value={dados.motorista_id}
          onChange={(e) => setDados({ ...dados, motorista_id: e.target.value })}
        >
          <option value="">Sem motorista</option>
          {motoristas.data?.map((m) => (
            <option key={m.id} value={m.id}>
              {m.nome}
            </option>
          ))}
        </select>
        <select
          className="input md:col-span-2"
          value={dados.status}
          onChange={(e) => setDados({ ...dados, status: e.target.value as StatusRota })}
        >
          <option value="ATIVA">Ativa</option>
          <option value="INATIVA">Inativa</option>
        </select>
        <button className="btn md:col-span-2">Salvar rota</button>
        {msgDados &&
          (msgDados.ok ? <Success text={msgDados.text} /> : <p role="alert" className="text-red-700 md:col-span-2">{msgDados.text}</p>)}
      </form>

      {/* Paradas */}
      <section className="card space-y-3">
        <h2 className="font-semibold">Paradas ({r.paradas.length})</h2>
        <MapaFrota
          altura="h-64"
          paradas={r.paradas.map((p) => ({ lat: p.latitude, lng: p.longitude, nome: p.nome, ordem: p.ordem }))}
          onClick={(p) => setNp((atual) => ({ ...atual, latitude: p.lat.toFixed(6), longitude: p.lng.toFixed(6) }))}
          ajusteKey={r.id}
        />
        <p className="text-xs text-slate-500">Toque no mapa para preencher a latitude e a longitude da nova parada.</p>
        <form onSubmit={adicionarParada} className="grid gap-2 md:grid-cols-4">
          <input
            className="input md:col-span-2"
            required
            maxLength={120}
            placeholder="Nome da parada"
            value={np.nome}
            onChange={(e) => setNp({ ...np, nome: e.target.value })}
          />
          <input
            className="input"
            required
            inputMode="decimal"
            placeholder="Latitude (-9.66)"
            value={np.latitude}
            onChange={(e) => setNp({ ...np, latitude: e.target.value })}
          />
          <input
            className="input"
            required
            inputMode="decimal"
            placeholder="Longitude (-35.73)"
            value={np.longitude}
            onChange={(e) => setNp({ ...np, longitude: e.target.value })}
          />
          <button className="btn md:col-span-4">Adicionar parada</button>
        </form>

        {r.paradas.length === 0 && <p className="text-slate-500">Nenhuma parada cadastrada.</p>}
        <ul className="divide-y">
          {r.paradas.map((p, i) => (
            <li key={p.id} className="space-y-2 py-2">
              {editP?.id === p.id ? (
                <div className="grid gap-2 md:grid-cols-4">
                  <input
                    className="input md:col-span-2"
                    value={editP.nome}
                    onChange={(e) => setEditP({ ...editP, nome: e.target.value })}
                  />
                  <input
                    className="input"
                    inputMode="decimal"
                    value={editP.latitude}
                    onChange={(e) => setEditP({ ...editP, latitude: e.target.value })}
                  />
                  <input
                    className="input"
                    inputMode="decimal"
                    value={editP.longitude}
                    onChange={(e) => setEditP({ ...editP, longitude: e.target.value })}
                  />
                  <div className="flex gap-2 md:col-span-4">
                    <button className="btn" onClick={salvarParada}>
                      Salvar
                    </button>
                    <button className="btn-ghost" onClick={() => setEditP(null)}>
                      Cancelar
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <p className="font-medium">
                      {i + 1}. {p.nome}
                    </p>
                    <p className="text-xs text-slate-500">
                      {p.latitude}, {p.longitude}
                    </p>
                  </div>
                  <div className="flex flex-wrap justify-end gap-1">
                    <button className="btn-ghost" disabled={i === 0} onClick={() => mover(r.paradas, i, -1)} aria-label="Subir">
                      <ChevronUp className="h-4 w-4" />
                    </button>
                    <button
                      className="btn-ghost"
                      disabled={i === r.paradas.length - 1}
                      onClick={() => mover(r.paradas, i, 1)}
                      aria-label="Descer"
                    >
                      <ChevronDown className="h-4 w-4" />
                    </button>
                    <button
                      className="btn-ghost"
                      onClick={() =>
                        setEditP({ id: p.id, nome: p.nome, latitude: String(p.latitude), longitude: String(p.longitude) })
                      }
                    >
                      Editar
                    </button>
                    <button
                      className="btn-ghost text-red-700"
                      onClick={() => {
                        if (confirm(`Excluir a parada "${p.nome}"? Os alunos dela ficam sem parada.`))
                          acao(() => api(`${base}/paradas/${p.id}`, { method: "DELETE" }));
                      }}
                    >
                      Excluir
                    </button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      </section>

      {/* Alunos */}
      <section className="card space-y-3">
        <h2 className="font-semibold">
          Alunos ({r.alunos.length}
          {veiculoAtual ? ` / ${veiculoAtual.capacidade}` : ""})
        </h2>
        <form onSubmit={vincular} className="grid gap-2 md:grid-cols-2">
          <select className="input" required value={alunoSel} onChange={(e) => setAlunoSel(e.target.value)}>
            <option value="">Escolha o aluno…</option>
            {disponiveis.map((a) => (
              <option key={a.id} value={a.id}>
                {a.nome}
              </option>
            ))}
          </select>
          <select className="input" value={paradaSel} onChange={(e) => setParadaSel(e.target.value)}>
            <option value="">Sem parada</option>
            {r.paradas.map((p) => (
              <option key={p.id} value={p.id}>
                {p.ordem}. {p.nome}
              </option>
            ))}
          </select>
          <button className="btn md:col-span-2">Adicionar aluno à rota</button>
        </form>

        {r.alunos.length === 0 && <p className="text-slate-500">Nenhum aluno nesta rota.</p>}
        <ul className="divide-y">
          {r.alunos.map((a) => (
            <li key={a.aluno_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <div>
                <p className="font-medium">{a.nome}</p>
                <p className="text-xs text-slate-500">{a.escola}</p>
              </div>
              <div className="flex items-center gap-2">
                <select
                  className="input !w-auto !py-2 text-sm"
                  value={a.parada_id ?? ""}
                  onChange={(e) =>
                    acao(() =>
                      api(`${base}/alunos/${a.aluno_id}`, {
                        method: "PATCH",
                        body: JSON.stringify({ parada_id: e.target.value ? Number(e.target.value) : null }),
                      }),
                    )
                  }
                >
                  <option value="">Sem parada</option>
                  {r.paradas.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.ordem}. {p.nome}
                    </option>
                  ))}
                </select>
                <button
                  className="btn-ghost text-red-700"
                  onClick={() => acao(() => api(`${base}/alunos/${a.aluno_id}`, { method: "DELETE" }))}
                >
                  Remover
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}