"use client";
import { useEffect, useState } from "react";
import { mostrarNotificacao } from "@/lib/useAvisos";

type Estado = NotificationPermission | "indisponivel";

export function PermissaoNotificacao() {
  const [estado, setEstado] = useState<Estado | null>(null);

  useEffect(() => {
    setEstado("Notification" in window ? Notification.permission : "indisponivel");
  }, []);

  async function ativar() {
    const r = await Notification.requestPermission();
    setEstado(r);
    if (r === "granted") mostrarNotificacao("Notificações ativadas", "Você será avisado quando a van sair ou estiver chegando.", "teste");
  }

  if (estado === null) return null;

  if (estado === "granted")
    return (
      <p className="callout callout-ok">
        Notificações ativadas neste aparelho. Você é avisado enquanto o aplicativo estiver aberto ou em segundo plano.
      </p>
    );
  if (estado === "denied")
    return (
      <p className="callout callout-warn">
        As notificações estão bloqueadas neste aparelho. Libere nas configurações do navegador para receber os avisos da van.
      </p>
    );
  if (estado === "indisponivel")
    return (
      <p className="callout">
        Este navegador não oferece notificações. No iPhone, adicione o aplicativo à Tela de Início para usá-las.
      </p>
    );
  return (
    <div className="card flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-sm">Receba um aviso no aparelho quando a van sair, estiver chegando à sua parada ou terminar a viagem.</p>
      <button className="btn shrink-0" onClick={ativar}>
        Ativar notificações
      </button>
    </div>
  );
}