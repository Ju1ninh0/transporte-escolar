"use client";
import { useState } from "react";
import { Empty, ErrorBox, Loading } from "@/components/StateViews";
import { fmtData, GRAVIDADES, type Filho, type Gravidade, type OcorrenciaFilho } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const COR: Record<Gravidade, string> = {
  LEVE: "badge-neutral",
  MEDIA: "badge-warn",
  GRAVE: "badge-danger",
};

export default function OcorrenciasResponsavel() {
  const [aluno, setAluno] = useState("");
  const filhos = useApi<Filho[]>("/responsavel/filhos");
  const ocorrencias = useApi<OcorrenciaFilho[]>(`/responsavel/ocorrencias${aluno ? `?aluno_id=${aluno}` : ""}`);

  return (
    <div className="space-y-4">
      <h1 className="page-title">Ocorrências</h1>

      {filhos.data && filhos.data.length > 1 && (
        <div className="card">
          <select className="input" value={aluno} onChange={(e) => setAluno(e.target.value)}>
            <option value="">Todos os filhos</option>
            {filhos.data.map((f) => (
              <option key={f.id} value={f.id}>
                {f.nome}
              </option>
            ))}
          </select>
        </div>
      )}

      {ocorrencias.loading && !ocorrencias.data && <Loading />}
      {ocorrencias.error && <ErrorBox message={ocorrencias.error} onRetry={ocorrencias.reload} />}
      {ocorrencias.data && ocorrencias.data.length === 0 && <Empty text="Nenhuma ocorrência registrada." />}

      {ocorrencias.data?.map((o) => (
        <div key={o.id} className="card space-y-1">
          <div className="flex items-start justify-between gap-2">
            <p className="font-semibold">
              {o.aluno_nome} · {o.tipo_nome}
            </p>
            <span className={`badge ${COR[o.gravidade]}`}>
              {GRAVIDADES.find((g) => g.value === o.gravidade)?.label}
            </span>
          </div>
          <p className="text-sm text-slate-500">{fmtData(o.data)}</p>
          <p>{o.descricao}</p>
          {o.consequencia && (
            <p className="text-sm">
              <span className="text-slate-500">Consequência: </span>
              {o.consequencia}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}