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
        <p className="text-slate-500">Motoristas cadastrados no sistema.</p>
      </div>

      {loading && <Loading />}

      {error && <ErrorBox message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <Empty text="Nenhum motorista cadastrado." />
      )}

      {data?.map((motorista) => (
        <div key={motorista.id} className="card">
          <p className="font-semibold">Motorista #{motorista.id}</p>
          <p className="text-sm text-slate-500">
            Usuário: #{motorista.usuario_id}
          </p>
        </div>
      ))}
    </div>
  );
}