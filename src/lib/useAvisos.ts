"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Aviso } from "@/lib/types";

const CHAVE = "te:ultimo-aviso";

/** Mostra uma notificação do sistema (pela service worker, quando existe). */
export async function mostrarNotificacao(titulo: string, corpo: string, tag: string) {
  try {
    const reg = "serviceWorker" in navigator ? await navigator.serviceWorker.getRegistration() : undefined;
    const opcoes = { body: corpo, tag, icon: "/icons/icon-192.png", badge: "/icons/icon-192.png", data: { url: "/responsavel/avisos" } };
    if (reg) await reg.showNotification(titulo, opcoes);
    else new Notification(titulo, opcoes);
  } catch {
    /* sem permissão ou sem suporte: ignora */
  }
}

/**
 * Consulta os avisos do responsável a cada 20 s. Devolve quantos estão sem ler e,
 * se o aparelho liberou notificações, avisa na hora quando chega um aviso novo.
 */
export function useAvisosNaoLidas(ativo: boolean) {
  const [naoLidas, setNaoLidas] = useState(0);

  const verificar = useCallback(async () => {
    try {
      const visto = localStorage.getItem(CHAVE);
      if (visto === null) {
        // primeira vez neste aparelho: só marca o ponto de partida, sem despejar notificações antigas
        const todas = await api<Aviso[]>("/responsavel/avisos");
        localStorage.setItem(CHAVE, String(Math.max(0, ...todas.map((a) => a.id))));
        setNaoLidas(todas.filter((a) => !a.lida).length);
        return;
      }
      const resumo = await api<{ nao_lidas: number }>("/responsavel/avisos/resumo");
      setNaoLidas(resumo.nao_lidas);
      if (resumo.nao_lidas === 0) return;

      const lista = await api<Aviso[]>("/responsavel/avisos?somente_nao_lidas=true");
      const novos = lista.filter((a) => a.id > Number(visto)).sort((a, b) => a.id - b.id);
      if (novos.length === 0) return;
      localStorage.setItem(CHAVE, String(novos[novos.length - 1].id));
      if ("Notification" in window && Notification.permission === "granted") {
        for (const a of novos.slice(-3)) await mostrarNotificacao(a.titulo, a.mensagem, `aviso-${a.id}`);
      }
    } catch {
      /* sem rede: tenta de novo no próximo ciclo */
    }
  }, []);

  useEffect(() => {
    if (!ativo) return;
    verificar();
    const t = setInterval(verificar, 20000);
    const aoVoltar = () => {
      if (document.visibilityState === "visible") verificar();
    };
    document.addEventListener("visibilitychange", aoVoltar);
    return () => {
      clearInterval(t);
      document.removeEventListener("visibilitychange", aoVoltar);
    };
  }, [ativo, verificar]);

  return naoLidas;
}