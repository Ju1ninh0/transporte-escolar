"use client";
import { Empty, ErrorBox, Loading } from "@/components/StateViews";
import { useAuth } from "@/lib/auth";
import type { Aluno } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function MotoristaHome() {
  const { user } = useAuth();
  const { data, error, loading, reload } = useApi<Aluno[]>("/alunos");

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Olá, {user?.nome.split(" ")[0]}</h1>
      <p className="text-slate-500">Rotas e GPS chegam na fase 3.</p>
      <h2 className="font-semibold">Alunos das suas rotas</h2>
      {loading && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data && data.length === 0 && <Empty text="Nenhum aluno atribuído." />}
      {data?.map((a) => (
        <div key={a.id} className="card">
          {a.nome} <span className="text-slate-500">· {a.escola}</span>
        </div>
      ))}
    </div>
  );
}
