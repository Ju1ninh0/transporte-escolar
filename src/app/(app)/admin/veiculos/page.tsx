"use client";
import { useState } from "react";
import { Empty, ErrorBox, Loading, Success } from "@/components/StateViews";
import { api } from "@/lib/api";
import type { Veiculo } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Msg = { ok: boolean; text: string } | null;
const vazio = { placa: "", apelido: "", capacidade: "15" };

export default function VeiculosPage() {
  const veiculos = useApi<Veiculo[]>("/veiculos");
  const [f, setF] = useState(vazio);
  const [msg, setMsg] = useState<Msg>(null);
  const [edit, setEdit] = useState<{ id: number; placa: string; apelido: string; capacidade: string } | null>(null);
  const [msgEdit, setMsgEdit] = useState<Msg>(null);

  async function criar(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      await api("/veiculos", {
        method: "POST",
        body: JSON.stringify({ placa: f.placa, apelido: f.apelido, capacidade: Number(f.capacidade) }),
      });
      setF(vazio);
      setMsg({ ok: true, text: "Veículo cadastrado." });
      veiculos.reload();
    } catch (err) {
      setMsg({ ok: false, text: (err as Error).message });
    }
  }

  async function salvar() {
    if (!edit) return;
    setMsgEdit(null);
    try {
      await api(`/veiculos/${edit.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          placa: edit.placa,
          apelido: edit.apelido,
          capacidade: Number(edit.capacidade),
        }),
      });
      setEdit(null);
      veiculos.reload();
    } catch (err) {
      setMsgEdit({ ok: false, text: (err as Error).message });
    }
  }

  async function alternar(v: Veiculo) {
    setMsgEdit(null);
    try {
      await api(`/veiculos/${v.id}`, { method: "PATCH", body: JSON.stringify({ ativo: !v.ativo }) });
      veiculos.reload();
    } catch (err) {
      setMsgEdit({ ok: false, text: (err as Error).message });
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="page-title">Veículos</h1>

      <form onSubmit={criar} className="card grid gap-3 md:grid-cols-3">
        <h2 className="font-semibold md:col-span-3">Novo veículo</h2>
        <input
          className="input"
          required
          placeholder="Placa (ABC1D23)"
          maxLength={15}
          value={f.placa}
          onChange={(e) => setF({ ...f, placa: e.target.value })}
        />
        <input
          className="input"
          required
          placeholder="Apelido (ex.: Van 1)"
          maxLength={60}
          value={f.apelido}
          onChange={(e) => setF({ ...f, apelido: e.target.value })}
        />
        <input
          className="input"
          type="number"
          required
          min={1}
          max={100}
          placeholder="Capacidade"
          value={f.capacidade}
          onChange={(e) => setF({ ...f, capacidade: e.target.value })}
        />
        <button className="btn md:col-span-3">Cadastrar veículo</button>
        {msg && (msg.ok ? <Success text={msg.text} /> : <p role="alert" className="text-red-700 md:col-span-3">{msg.text}</p>)}
      </form>

      {msgEdit && !msgEdit.ok && (
        <p role="alert" className="text-red-700">
          {msgEdit.text}
        </p>
      )}
      {veiculos.loading && !veiculos.data && <Loading />}
      {veiculos.error && <ErrorBox message={veiculos.error} onRetry={veiculos.reload} />}
      {veiculos.data && veiculos.data.length === 0 && <Empty text="Nenhum veículo cadastrado." />}

      {veiculos.data?.map((v) => (
        <div key={v.id} className="card space-y-2">
          {edit?.id === v.id ? (
            <div className="grid gap-2 md:grid-cols-3">
              <input
                className="input"
                value={edit.placa}
                maxLength={15}
                onChange={(e) => setEdit({ ...edit, placa: e.target.value })}
              />
              <input
                className="input"
                value={edit.apelido}
                maxLength={60}
                onChange={(e) => setEdit({ ...edit, apelido: e.target.value })}
              />
              <input
                className="input"
                type="number"
                min={1}
                max={100}
                value={edit.capacidade}
                onChange={(e) => setEdit({ ...edit, capacidade: e.target.value })}
              />
              <div className="flex gap-2 md:col-span-3">
                <button className="btn" onClick={salvar}>
                  Salvar
                </button>
                <button className="btn-ghost" onClick={() => setEdit(null)}>
                  Cancelar
                </button>
              </div>
              {msgEdit && !msgEdit.ok && (
                <p role="alert" className="text-red-700 md:col-span-3">
                  {msgEdit.text}
                </p>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-between gap-2">
              <div className={v.ativo ? "" : "text-slate-400"}>
                <p className="font-semibold">
                  {v.apelido} · {v.placa}
                </p>
                <p className="text-sm">
                  Capacidade: {v.capacidade} {v.ativo ? "" : "· inativo"}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  className="btn-ghost"
                  onClick={() => {
                    setMsgEdit(null);
                    setEdit({ id: v.id, placa: v.placa, apelido: v.apelido, capacidade: String(v.capacidade) });
                  }}
                >
                  Editar
                </button>
                <button className="btn-ghost" onClick={() => alternar(v)}>
                  {v.ativo ? "Desativar" : "Reativar"}
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}