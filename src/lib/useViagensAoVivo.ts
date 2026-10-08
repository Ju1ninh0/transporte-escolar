"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, tokenAtual } from "@/lib/api";
import type { PosicaoVan, ViagemAtiva } from "@/lib/types";

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/^http/, "ws");

function maisRecente(a: PosicaoVan | null, b: PosicaoVan | null): PosicaoVan | null {
  if (!a) return b;
  if (!b) return a;
  return Date.parse(b.timestamp) >= Date.parse(a.timestamp) ? b : a;
}

/**
 * Viagens em andamento com a última posição de cada van.
 * Usa o WebSocket para atualizar em tempo real e uma consulta a cada 10 s como reforço
 * (pega viagens novas e remove as encerradas). O admin usa /viagens/ativas; o responsável,
 * /responsavel/viagens/ativas (só as rotas dos filhos dele).
 */
export function useViagensAoVivo(caminhoAtivas: string = "/viagens/ativas") {
  const [viagens, setViagens] = useState<ViagemAtiva[]>([]);
  const [conectado, setConectado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);
  const atuais = useRef<ViagemAtiva[]>([]);
  atuais.current = viagens;

  const mesclar = useCallback((novas: ViagemAtiva[]) => {
    setViagens((antigas) =>
      novas.map((n) => {
        const antiga = antigas.find((a) => a.viagem_id === n.viagem_id);
        return { ...n, posicao: maisRecente(antiga?.posicao ?? null, n.posicao) };
      }),
    );
  }, []);

  const recarregar = useCallback(async () => {
    try {
      mesclar(await api<ViagemAtiva[]>(caminhoAtivas));
      setErro(null);
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
  }, [mesclar, caminhoAtivas]);

  useEffect(() => {
    recarregar();
    const t = setInterval(recarregar, 10000);
    return () => clearInterval(t);
  }, [recarregar]);

  useEffect(() => {
    let ativo = true;
    let ws: WebSocket | null = null;
    let religar: ReturnType<typeof setTimeout> | undefined;
    let ping: ReturnType<typeof setInterval> | undefined;

    async function conectar() {
      if (!ativo) return;
      const token = await tokenAtual();
      if (!token || !ativo) return;
      const socket = new WebSocket(`${WS_BASE}/api/v1/ws/viagens`);
      ws = socket;
      socket.onopen = () => {
        socket.send(JSON.stringify({ token }));
        ping = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) socket.send("ping");
        }, 25000);
      };
      socket.onmessage = (ev) => {
        const msg = JSON.parse(ev.data as string);
        if (msg.tipo === "snapshot") {
          setConectado(true);
          mesclar(msg.viagens as ViagemAtiva[]);
        } else if (msg.tipo === "localizacao") {
          const nova: PosicaoVan = {
            latitude: msg.latitude,
            longitude: msg.longitude,
            velocidade: msg.velocidade,
            direcao: msg.direcao,
            timestamp: msg.timestamp,
          };
          if (!atuais.current.some((v) => v.viagem_id === msg.viagem_id)) {
            recarregar(); // viagem nova que ainda não conhecemos
            return;
          }
          setViagens((lista) =>
            lista.map((v) => (v.viagem_id === msg.viagem_id ? { ...v, posicao: maisRecente(v.posicao, nova) } : v)),
          );
        }
      };
      socket.onclose = (ev) => {
        clearInterval(ping);
        setConectado(false);
        if (!ativo || ev.code === 4403) return;
        if (ev.code === 4401) api("/auth/me").catch(() => {}); // renova o token antes de reconectar
        religar = setTimeout(conectar, 3000);
      };
      socket.onerror = () => socket.close();
    }

    conectar();
    return () => {
      ativo = false;
      clearTimeout(religar);
      clearInterval(ping);
      ws?.close();
    };
  }, [mesclar, recarregar]);

  return { viagens, conectado, erro, carregando, recarregar };
}