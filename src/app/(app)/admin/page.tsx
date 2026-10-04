"use client";
import { useEffect, useState } from "react";
import { ErrorBox, Loading, Success } from "@/components/StateViews";
import { api } from "@/lib/api";
import type { Configuracoes, PixConfig } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Msg = { ok: boolean; text: string } | null;

const TIPOS_CHAVE = ["CPF", "CNPJ", "EMAIL", "TELEFONE", "ALEATORIA"];
const pixVazio: PixConfig = { recebedor: "", tipo_chave: "CPF", chave: "", mensagem: "" };

function Aviso({ msg }: { msg: Msg }) {
  if (!msg) return null;
  return msg.ok ? <Success text={msg.text} /> : <p role="alert" className="text-red-700">{msg.text}</p>;
}

export default function ConfiguracoesPage() {
  const cfg = useApi<Configuracoes>("/configuracoes");

  const [pix, setPix] = useState<PixConfig>(pixVazio);
  const [metros, setMetros] = useState("");
  const [regras, setRegras] = useState<Record<number, string>>({});
  const [msgGeral, setMsgGeral] = useState<Msg>(null);
  const [msgRegra, setMsgRegra] = useState<(Msg & { numero: number }) | null>(null);

  // Preenche os formulários quando os dados chegam
  useEffect(() => {
    if (!cfg.data) return;
    setPix({ ...pixVazio, ...cfg.data.pix });
    setMetros(cfg.data.proximidade_metros?.toString() ?? "");
    setRegras(Object.fromEntries(cfg.data.regras_reincidencia.map((r) => [r.numero_ocorrencia, r.consequencia])));
  }, [cfg.data]);

  const setP = (k: keyof PixConfig) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setPix({ ...pix, [k]: e.target.value });

  async function salvarGeral(e: React.FormEvent) {
    e.preventDefault();
    setMsgGeral(null);
    const body: Record<string, unknown> = {};
    // O PIX só é enviado se estiver preenchido (o backend exige recebedor e chave)
    if (pix.recebedor.trim() || pix.chave.trim()) body.pix = pix;
    if (metros.trim()) body.proximidade_metros = Number(metros);
    if (Object.keys(body).length === 0) {
      setMsgGeral({ ok: false, text: "Nada para salvar." });
      return;
    }
    try {
      await api("/configuracoes", { method: "PATCH", body: JSON.stringify(body) });
      setMsgGeral({ ok: true, text: "Configurações salvas." });
      cfg.reload();
    } catch (err) {
      setMsgGeral({ ok: false, text: (err as Error).message });
    }
  }

  async function salvarRegra(numero: number) {
    setMsgRegra(null);
    try {
      await api(`/configuracoes/regras-reincidencia/${numero}`, {
        method: "PATCH",
        body: JSON.stringify({ consequencia: regras[numero] ?? "" }),
      });
      setMsgRegra({ ok: true, text: "Regra salva.", numero });
      cfg.reload();
    } catch (err) {
      setMsgRegra({ ok: false, text: (err as Error).message, numero });
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="page-title">Configurações</h1>
      {cfg.loading && !cfg.data && <Loading />}
      {cfg.error && <ErrorBox message={cfg.error} onRetry={cfg.reload} />}

      {cfg.data && (
        <>
          <form onSubmit={salvarGeral} className="card grid gap-3 md:grid-cols-2">
            <h2 className="font-semibold md:col-span-2">PIX para pagamentos</h2>
            <input
              className="input"
              maxLength={120}
              placeholder="Nome do recebedor"
              value={pix.recebedor}
              onChange={setP("recebedor")}
            />
            <select className="input" value={pix.tipo_chave} onChange={setP("tipo_chave")}>
              {TIPOS_CHAVE.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <input
              className="input md:col-span-2"
              maxLength={140}
              placeholder="Chave PIX"
              value={pix.chave}
              onChange={setP("chave")}
            />
            <input
              className="input md:col-span-2"
              maxLength={140}
              placeholder="Mensagem (opcional)"
              value={pix.mensagem}
              onChange={setP("mensagem")}
            />

            <h2 className="mt-2 font-semibold md:col-span-2">Aproximação da van</h2>
            <label className="md:col-span-2">
              <span className="mb-1 block text-sm text-slate-600">Distância para avisar o responsável (metros)</span>
              <input
                className="input"
                type="number"
                min={1}
                max={100000}
                placeholder="Ex.: 500"
                value={metros}
                onChange={(e) => setMetros(e.target.value)}
              />
            </label>

            <button className="btn md:col-span-2">Salvar configurações</button>
            <div className="md:col-span-2">
              <Aviso msg={msgGeral} />
            </div>
          </form>

          <section className="card space-y-3">
            <h2 className="font-semibold">Regras de reincidência</h2>
            <p className="text-sm text-slate-600">
              A consequência sugerida ao registrar uma ocorrência, conforme o número de ocorrências do aluno.
            </p>
            {cfg.data.regras_reincidencia.length === 0 && (
              <p className="text-slate-500">Nenhuma regra cadastrada.</p>
            )}
            {cfg.data.regras_reincidencia.map((r) => (
              <div key={r.numero_ocorrencia} className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="w-20 shrink-0 text-sm font-semibold">{r.numero_ocorrencia}ª ocorr.</span>
                  <input
                    className="input flex-1"
                    maxLength={120}
                    value={regras[r.numero_ocorrencia] ?? ""}
                    onChange={(e) => setRegras({ ...regras, [r.numero_ocorrencia]: e.target.value })}
                  />
                  <button
                    className="btn-ghost"
                    disabled={
                      !(regras[r.numero_ocorrencia] ?? "").trim() ||
                      regras[r.numero_ocorrencia] === r.consequencia
                    }
                    onClick={() => salvarRegra(r.numero_ocorrencia)}
                  >
                    Salvar
                  </button>
                </div>
                {msgRegra?.numero === r.numero_ocorrencia && <Aviso msg={msgRegra} />}
              </div>
            ))}
          </section>
        </>
      )}
    </div>
  );
}
