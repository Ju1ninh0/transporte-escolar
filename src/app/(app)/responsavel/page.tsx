"use client";
import { Empty, ErrorBox, Loading } from "@/components/StateViews";
import { useAuth } from "@/lib/auth";
import type { Aluno } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function ResponsavelHome() {
  const { user } = useAuth();
  const { data, error, loading, reload } = useApi<Aluno[]>("/alunos");

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Olá, {user?.nome.split(" ")[0]}</h1>
      {loading && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data && data.length === 0 && <Empty text="Nenhum filho cadastrado." />}
      {data?.map((a) => (
        <div key={a.id} className="card">
          <p className="text-lg font-semibold">{a.nome}</p>
          <p className="text-slate-600">
            {a.escola}
            {a.serie ? ` · ${a.serie}` : ""}
          </p>
          <p className="mt-2 text-sm text-slate-400">Frequência e financeiro chegam na próxima fase.</p>
        </div>
      ))}
    </div>
  );
}
