"use client";
import { useEffect, useState } from "react";
import { Empty, ErrorBox, Loading, Success } from "@/components/StateViews";
import { api } from "@/lib/api";
import {
  GRAVIDADES,
  fmtData,
  type Aluno,
  type Gravidade,
  type Ocorrencia,
  type SugestaoConsequencia,
  type TipoOcorrencia,
} from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Msg = { ok: boolean; text: string } | null;

const hoje = () => new Date().toLocaleDateString("sv-SE"); // YYYY-MM-DD no fuso local
const vazio = {
  aluno_id: "",
  tipo_id: "",
  data: hoje(),
  gravidade: "LEVE" as Gravidade,
  descricao: "",
  consequencia: "",
};

const corGravidade: Record<Gravidade, string> = {
  LEVE: "bg-slate-100 text-slate-700",
  MEDIA: "bg-amber-100 text-amber-800",
  GRAVE: "bg-red-100 text-red-800",
};

export default function OcorrenciasPage() {
  const [filtroAluno, setFiltroAluno] = useState("");
  const [filtroGrav, setFiltroGrav] = useState("");
  const qs = new URLSearchParams();
  if (filtroAluno) qs.set("aluno_id", filtroAluno);
  if (filtroGrav) qs.set("gravidade", filtroGrav);
  const query = qs.toString();

  const ocorrencias = useApi<Ocorrencia[]>(`/ocorrencias${query ? `?${query}` : ""}`);
  const alunos = useApi<Aluno[]>("/alunos");
  const tipos = useApi<TipoOcorrencia[]>("/tipos-ocorrencia");

  const [f, setF] = useState(vazio);
  const [sugestao, setSugestao] = useState<SugestaoConsequencia | null>(null);
  const [msg, setMsg] = useState<Msg>(null);
  const [editando, setEditando] = useState<{ id: number; texto: string } | null>(null);
  const [novoTipo, setNovoTipo] = useState("");
  const [msgTipo, setMsgTipo] = useState<Msg>(null);

  const set =
    (k: keyof typeof vazio) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setF({ ...f, [k]: e.target.value });

  // Ao escolher o aluno, busca a sugestão de consequência (reincidência)
  useEffect(() => {
    if (!f.aluno_id) {
      setSugestao(null);
      return;
    }
    let ativo = true;
    api<SugestaoConsequencia>(`/ocorrencias/sugestao-consequencia?aluno_id=${f.aluno_id}`)
      .then((s) => ativo && setSugestao(s))
      .catch(() => ativo && setSugestao(null));
    return () => {
      ativo = false;
    };
  }, [f.aluno_id]);

  async function criar(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      await api("/ocorrencias", {
        method: "POST",
        body: JSON.stringify({
          aluno_id: Number(f.aluno_id),
          tipo_id: Number(f.tipo_id),
          data: f.data,
          gravidade: f.gravidade,
          descricao: f.descricao,
          consequencia: f.consequencia.trim() || null,
        }),
      });
      setF({ ...vazio, data: hoje() });
      setSugestao(null);
      setMsg({ ok: true, text: "Ocorrência registrada." });
      ocorrencias.reload();
    } catch (err) {
      setMsg({ ok: false, text: (err as Error).message });
    }
  }

  async function salvarConsequencia() {
    if (!editando) return;
    try {
      await api(`/ocorrencias/${editando.id}`, {
        method: "PATCH",
        body: JSON.stringify({ consequencia: editando.texto.trim() || null }),
      });
      setEditando(null);
      ocorrencias.reload();
    } catch (err) {
      setMsg({ ok: false, text: (err as Error).message });
    }
  }

  async function criarTipo(e: React.FormEvent) {
    e.preventDefault();
    setMsgTipo(null);
    try {
      await api("/tipos-ocorrencia", { method: "POST", body: JSON.stringify({ nome: novoTipo }) });
      setNovoTipo("");
      tipos.reload();
    } catch (err) {
      setMsgTipo({ ok: false, text: (err as Error).message });
    }
  }

  async function alternarTipo(t: TipoOcorrencia) {
    setMsgTipo(null);
    try {
      await api(`/tipos-ocorrencia/${t.id}`, {
        method: "PATCH",
        body: JSON.stringify({ ativo: !t.ativo }),
      });
      tipos.reload();
    } catch (err) {
      setMsgTipo({ ok: false, text: (err as Error).message });
    }
  }

  const tiposAtivos = tipos.data?.filter((t) => t.ativo) ?? [];
  const alunosAtivos = alunos.data?.filter((a) => a.ativo) ?? [];

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Ocorrências</h1>

      <form onSubmit={criar} className="card grid gap-3 md:grid-cols-2">
        <h2 className="font-semibold md:col-span-2">Nova ocorrência</h2>
        <select className="input" required value={f.aluno_id} onChange={set("aluno_id")}>
          <option value="">Aluno…</option>
          {alunosAtivos.map((a) => (
            <option key={a.id} value={a.id}>
              {a.nome}
            </option>
          ))}
        </select>
        <select className="input" required value={f.tipo_id} onChange={set("tipo_id")}>
          <option value="">Tipo…</option>
          {tiposAtivos.map((t) => (
            <option key={t.id} value={t.id}>
              {t.nome}
            </option>
          ))}
        </select>
        <input className="input" type="date" required value={f.data} onChange={set("data")} />
        <select className="input" value={f.gravidade} onChange={set("gravidade")}>
          {GRAVIDADES.map((g) => (
            <option key={g.value} value={g.value}>
              {g.label}
            </option>
          ))}
        </select>
        <textarea
          className="input md:col-span-2"
          rows={3}
          required
          placeholder="Descrição"
          value={f.descricao}
          onChange={set("descricao")}
        />
        <input
          className="input md:col-span-2"
          maxLength={120}
          placeholder="Consequência (opcional)"
          value={f.consequencia}
          onChange={set("consequencia")}
        />
        {sugestao && (
          <div className="rounded-xl bg-slate-100 px-3 py-2 text-sm md:col-span-2">
            Esta será a <strong>{sugestao.numero_ocorrencia}ª</strong> ocorrência do aluno.{" "}
            {sugestao.consequencia ? (
              <>
                Sugestão: <strong>{sugestao.consequencia}</strong>{" "}
                <button
                  type="button"
                  className="text-emerald-700 underline"
                  onClick={() => setF({ ...f, consequencia: sugestao.consequencia ?? "" })}
                >
                  usar sugestão
                </button>
              </>
            ) : (
              "Nenhuma regra de reincidência se aplica."
            )}
          </div>
        )}
        <button className="btn md:col-span-2">Registrar ocorrência</button>
        {msg &&
          (msg.ok ? <Success text={msg.text} /> : <p role="alert" className="text-red-700">{msg.text}</p>)}
      </form>

      <section className="card space-y-3">
        <h2 className="font-semibold">Tipos de ocorrência</h2>
        <form onSubmit={criarTipo} className="flex gap-2">
          <input
            className="input flex-1"
            maxLength={80}
            required
            placeholder="Novo tipo"
            value={novoTipo}
            onChange={(e) => setNovoTipo(e.target.value)}
          />
          <button className="btn">Adicionar</button>
        </form>
        {msgTipo && !msgTipo.ok && (
          <p role="alert" className="text-red-700">
            {msgTipo.text}
          </p>
        )}
        {tipos.loading && <Loading />}
        {tipos.error && <ErrorBox message={tipos.error} onRetry={tipos.reload} />}
        {tipos.data && tipos.data.length === 0 && <Empty text="Nenhum tipo cadastrado." />}
        <ul className="divide-y">
          {tipos.data?.map((t) => (
            <li key={t.id} className="flex items-center justify-between py-2">
              <span className={t.ativo ? "" : "text-slate-400 line-through"}>{t.nome}</span>
              <button className="btn-ghost" onClick={() => alternarTipo(t)}>
                {t.ativo ? "Desativar" : "Reativar"}
              </button>
            </li>
          ))}
        </ul>
      </section>

      <div className="card grid gap-3 md:grid-cols-2">
        <select className="input" value={filtroAluno} onChange={(e) => setFiltroAluno(e.target.value)}>
          <option value="">Todos os alunos</option>
          {alunos.data?.map((a) => (
            <option key={a.id} value={a.id}>
              {a.nome}
            </option>
          ))}
        </select>
        <select className="input" value={filtroGrav} onChange={(e) => setFiltroGrav(e.target.value)}>
          <option value="">Todas as gravidades</option>
          {GRAVIDADES.map((g) => (
            <option key={g.value} value={g.value}>
              {g.label}
            </option>
          ))}
        </select>
      </div>

      {ocorrencias.loading && <Loading />}
      {ocorrencias.error && <ErrorBox message={ocorrencias.error} onRetry={ocorrencias.reload} />}
      {ocorrencias.data && ocorrencias.data.length === 0 && <Empty text="Nenhuma ocorrência encontrada." />}
      {ocorrencias.data?.map((o) => (
        <div key={o.id} className="card space-y-1">
          <div className="flex items-center justify-between gap-2">
            <p className="font-semibold">
              {o.aluno_nome} · {o.tipo_nome}
            </p>
            <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${corGravidade[o.gravidade]}`}>
              {GRAVIDADES.find((g) => g.value === o.gravidade)?.label}
            </span>
          </div>
          <p className="text-sm text-slate-500">
            {fmtData(o.data)} · registrada por {o.registrado_por_nome}
          </p>
          <p>{o.descricao}</p>
          {editando?.id === o.id ? (
            <div className="flex gap-2">
              <input
                className="input flex-1"
                maxLength={120}
                value={editando.texto}
                onChange={(e) => setEditando({ id: o.id, texto: e.target.value })}
              />
              <button className="btn" onClick={salvarConsequencia}>
                Salvar
              </button>
              <button className="btn-ghost" onClick={() => setEditando(null)}>
                Cancelar
              </button>
            </div>
          ) : (
            <p className="text-sm">
              <span className="text-slate-500">Consequência: </span>
              {o.consequencia ?? "—"}{" "}
              <button
                className="text-emerald-700 underline"
                onClick={() => setEditando({ id: o.id, texto: o.consequencia ?? "" })}
              >
                editar
              </button>
            </p>
          )}
        </div>
      ))}
    </div>
  );
}