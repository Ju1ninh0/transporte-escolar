"use client";

import { Empty, ErrorBox, Loading } from "@/components/StateViews";
import type { Motorista } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function MotoristasPage() {
  const { data, error, loading, reload } = useApi<Motorista[]>("/motoristas");

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Motoristas</h1>
        <p className="text-slate-500">
          Motoristas cadastrados no sistema.
        </p>
      </div>

      {loading && <Loading />}

      {error && <ErrorBox message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <Empty text="Nenhum motorista cadastrado." />
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {data?.map((motorista) => (
          <div key={motorista.id} className="card">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-lg font-semibold">{motorista.nome}</p>
                <p className="text-sm text-slate-500">
                  {motorista.email}
                </p>
                <p className="text-sm text-slate-500">
                  {motorista.telefone ?? "Telefone não informado"}
                </p>
              </div>

              <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-700">
                Ativo
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}