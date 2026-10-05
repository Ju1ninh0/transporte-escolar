"use client";
import { useEffect, useState } from "react";

type EventoInstalacao = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> };

const CHAVE = "te:instalar-dispensado";
const SETE_DIAS = 7 * 24 * 60 * 60 * 1000;

export function InstallPrompt() {
  const [evento, setEvento] = useState<EventoInstalacao | null>(null);
  const [ios, setIos] = useState(false);
  const [visivel, setVisivel] = useState(false);

  useEffect(() => {
    const instalado =
      window.matchMedia("(display-mode: standalone)").matches ||
      (navigator as unknown as { standalone?: boolean }).standalone === true;
    const dispensado = Number(localStorage.getItem(CHAVE) ?? 0);
    if (instalado || Date.now() - dispensado < SETE_DIAS) return;

    if (/iphone|ipad|ipod/i.test(navigator.userAgent)) {
      setIos(true);
      setVisivel(true);
    }
    const antes = (e: Event) => {
      e.preventDefault();
      setEvento(e as EventoInstalacao);
      setVisivel(true);
    };
    const depois = () => setVisivel(false);
    window.addEventListener("beforeinstallprompt", antes);
    window.addEventListener("appinstalled", depois);
    return () => {
      window.removeEventListener("beforeinstallprompt", antes);
      window.removeEventListener("appinstalled", depois);
    };
  }, []);

  function dispensar() {
    localStorage.setItem(CHAVE, String(Date.now()));
    setVisivel(false);
  }

  async function instalar() {
    if (!evento) return;
    await evento.prompt();
    const r = await evento.userChoice;
    if (r.outcome === "accepted") setVisivel(false);
    else dispensar();
    setEvento(null);
  }

  if (!visivel) return null;

  return (
    <div className="card flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="text-sm">
        <p className="font-medium">Instale o aplicativo</p>
        <p className="text-slate-600">
          {evento || !ios
            ? "Abra mais rápido pela tela inicial do celular e receba os avisos da van."
            : "No iPhone: toque em Compartilhar e depois em Adicionar à Tela de Início."}
        </p>
      </div>
      <div className="flex gap-2">
        {evento && (
          <button className="btn" onClick={instalar}>
            Instalar
          </button>
        )}
        <button className="btn-ghost" onClick={dispensar}>
          Agora não
        </button>
      </div>
    </div>
  );
}