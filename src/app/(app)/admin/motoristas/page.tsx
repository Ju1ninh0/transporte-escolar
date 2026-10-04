"use client";

import { useState } from "react";
import { Empty, ErrorBox, Loading } from "@/components/StateViews";
import type { Motorista } from "@/lib/types";
import { useApi } from "@/lib/useApi";
import { api } from "@/lib/api";

export default function MotoristasPage() {
  const { data, error, loading, reload } = useApi<Motorista[]>("/motoristas");

  const [mostrarForm, setMostrarForm] = useState(false);
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [telefone, setTelefone] = useState("");
  const [senha, setSenha] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [erroForm, setErroForm] = useState("");

  async function cadastrar(e: React.FormEvent) {
    e.preventDefault();
    setErroForm("");
    setSalvando(true);

    try {
      await api("/motoristas", {
        method: "POST",
        body: JSON.stringify({
          nome,
          email,
          telefone: telefone || null,
          senha,
        }),
      });

      setNome("");
      setEmail("");
      setTelefone("");
      setSenha("");
      setMostrarForm(false);
      reload();
    } catch (err) {
      setErroForm(err instanceof Error ? err.message : "Erro ao cadastrar motorista.");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="page-title">Motoristas</h1>
          <p className="text-slate-500">
            Motoristas cadastrados no sistema.
          </p>
        </div>

        <button
          type="button"
          className="btn"
          onClick={() => setMostrarForm((valor) => !valor)}
        >
          {mostrarForm ? "Cancelar" : "+ Novo motorista"}
        </button>
      </div>

      {mostrarForm && (
        <form onSubmit={cadastrar} className="card space-y-4">
          <h2 className="text-lg font-semibold">Cadastrar motorista</h2>

          <div>
            <label className="mb-1 block text-sm font-medium">Nome</label>
            <input
              className="w-full rounded-lg border px-3 py-2"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              required
              minLength={2}
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">E-mail</label>
            <input
              type="email"
              className="w-full rounded-lg border px-3 py-2"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">Telefone</label>
            <input
              className="w-full rounded-lg border px-3 py-2"
              value={telefone}
              onChange={(e) => setTelefone(e.target.value)}
              maxLength={20}
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">Senha</label>
            <input
              type="password"
              className="w-full rounded-lg border px-3 py-2"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              required
              minLength={8}
            />
          </div>

          {erroForm && <ErrorBox message={erroForm} />}

          <button
            type="submit"
            disabled={salvando}
            className="w-full btn"
          >
            {salvando ? "Cadastrando..." : "Cadastrar motorista"}
          </button>
        </form>
      )}

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

              <span className="badge badge-ok">
                Ativo
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}