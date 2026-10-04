"use client";
import { ChevronRight, Megaphone, Wallet } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";
import { Empty, ErrorBox, Loading } from "@/components/StateViews";
import { useAuth } from "@/lib/auth";
import type { Filho, Mensalidade } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const brl = (v: number) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export default function ResponsavelHome() {
  const { user } = useAuth();
  const filhos = useApi<Filho[]>("/responsavel/filhos");
  const avisos = useApi<{ nao_lidas: number }>("/responsavel/avisos/resumo");
  const mensalidades = useApi<Mensalidade[]>("/responsavel/mensalidades");

  // Atualiza a situação das viagens a cada 20 s
  const recarregarFilhos = filhos.reload;
  useEffect(() => {
    const t = setInterval(recarregarFilhos, 20000);
    return () => clearInterval(t);
  }, [recarregarFilhos]);

  const abertas = mensalidades.data?.filter((m) => m.status === "PENDENTE" || m.status === "ATRASADO") ?? [];
  const atrasadas = abertas.filter((m) => m.status === "ATRASADO");
  const totalAberto = abertas.reduce((soma, m) => soma + Number(m.saldo), 0);
  const naoLidas = avisos.data?.nao_lidas ?? 0;

  return (
    <div className="space-y-4">
      <h1 className="page-title">Olá, {user?.nome.split(" ")[0]}</h1>

      {naoLidas > 0 && (
        <Link href="/responsavel/avisos" className="callout callout-info flex items-center gap-2 py-3">
          <Megaphone className="h-4 w-4 shrink-0" />
          <span>Você tem <strong>{naoLidas}</strong> {naoLidas === 1 ? "aviso novo" : "avisos novos"}</span>
        </Link>
      )}

      {abertas.length > 0 && (
        <Link
          href="/responsavel/financeiro"
          className={`card block transition hover:bg-slate-50 ${atrasadas.length > 0 ? "card-danger" : ""}`}
        >
          <Wallet className="mr-2 inline h-4 w-4 align-text-bottom text-slate-500" />
          {atrasadas.length > 0 ? (
            <>
              <strong>{atrasadas.length}</strong> {atrasadas.length === 1 ? "mensalidade atrasada" : "mensalidades atrasadas"}
              {" · "}
            </>
          ) : null}
          Em aberto: <strong>{brl(totalAberto)}</strong>
        </Link>
      )}

      {filhos.loading && !filhos.data && <Loading />}
      {filhos.error && <ErrorBox message={filhos.error} onRetry={filhos.reload} />}
      {filhos.data && filhos.data.length === 0 && <Empty text="Nenhum filho cadastrado." />}

      {filhos.data?.map((f) => {
        const emViagem = f.rotas.some((r) => r.viagem_em_andamento_id !== null);
        return (
          <Link
            key={f.id}
            href={`/responsavel/filhos/${f.id}`}
            className={`card block space-y-1 transition hover:bg-slate-50 ${emViagem ? "card-live" : ""}`}
          >
            <div className="flex items-start justify-between gap-2">
              <p className="text-lg font-semibold">{f.nome}</p>
              {emViagem && (
                <span className="badge badge-ok">
                  <span className="mr-1.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                  Viagem em andamento
                </span>
              )}
            </div>
            <p className="text-slate-600">
              {f.escola}
              {f.serie ? ` · ${f.serie}` : ""}
            </p>
            {f.rotas.length === 0 ? (
              <p className="text-sm text-slate-400">Ainda não vinculado a uma rota.</p>
            ) : (
              f.rotas.map((r) => (
                <p key={r.rota_id} className="text-sm text-slate-600">
                  Rota: {r.rota_nome}
                  {r.parada_nome ? ` · parada: ${r.parada_nome}` : ""}
                </p>
              ))
            )}
            <p className="inline-flex items-center gap-1 pt-1 text-sm font-medium text-slate-900">
              Ver rota, van e presença
              <ChevronRight className="h-4 w-4" />
            </p>
          </Link>
        );
      })}
    </div>
  );
}