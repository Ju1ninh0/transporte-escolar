"use client";
import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  Bus,
  GraduationCap,
  Home,
  LayoutDashboard,
  LogOut,
  Map as MapIcon,
  Megaphone,
  Route,
  Settings,
  UserCheck,
  Users,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import type { Perfil } from "@/lib/types";

type Item = { href: string; label: string; icon: LucideIcon };

const MENU: Record<Perfil, Item[]> = {
  RESPONSAVEL: [
    { href: "/responsavel", label: "Início", icon: Home },
    { href: "/responsavel/financeiro", label: "Financeiro", icon: Wallet },
    { href: "/responsavel/ocorrencias", label: "Ocorrências", icon: AlertTriangle },
    { href: "/responsavel/avisos", label: "Avisos", icon: Megaphone },
  ],
  MOTORISTA: [{ href: "/motorista", label: "Início", icon: Home }],
  ADMIN: [
    { href: "/admin", label: "Painel", icon: LayoutDashboard },
    { href: "/admin/alunos", label: "Alunos", icon: GraduationCap },
    { href: "/admin/responsaveis", label: "Responsáveis", icon: Users },
    { href: "/admin/motoristas", label: "Motoristas", icon: UserCheck },
    { href: "/admin/financeiro", label: "Financeiro", icon: Wallet },
    { href: "/admin/veiculos", label: "Veículos", icon: Bus },
    { href: "/admin/rotas", label: "Rotas", icon: Route },
    { href: "/admin/mapa", label: "Mapa", icon: MapIcon },
    { href: "/admin/ocorrencias", label: "Ocorrências", icon: AlertTriangle },
    { href: "/admin/comunicados", label: "Avisos", icon: Megaphone },
    { href: "/admin/configuracoes", label: "Configurações", icon: Settings },
  ],
};

const PERFIL: Record<Perfil, string> = {
  ADMIN: "Administrador",
  MOTORISTA: "Motorista",
  RESPONSAVEL: "Responsável",
};

const HOMES = ["/admin", "/responsavel", "/motorista"];

export function Shell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const path = usePathname();
  const router = useRouter();
  if (!user) return null;
  const items = MENU[user.perfil];

  const ativo = (href: string) => (HOMES.includes(href) ? path === href : path === href || path.startsWith(`${href}/`));

  async function sair() {
    await logout();
    router.replace("/login");
  }

  const marca = (
    <div className="flex items-center gap-2.5">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-white">
        <Bus className="h-4 w-4" />
      </span>
      <span className="text-sm font-semibold tracking-tight">Transporte Escolar</span>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Barra lateral (computador) */}
      <aside className="hidden md:fixed md:inset-y-0 md:flex md:w-60 md:flex-col md:border-r md:border-slate-200 md:bg-white">
        <div className="px-4 py-4">{marca}</div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-4">
          {items.map((i) => {
            const Icon = i.icon;
            const on = ativo(i.href);
            return (
              <Link
                key={i.href}
                href={i.href}
                className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition ${
                  on ? "bg-slate-100 font-medium text-slate-900" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                }`}
              >
                <Icon className={`h-4 w-4 ${on ? "text-slate-900" : "text-slate-400"}`} />
                {i.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-200 p-3">
          <p className="truncate text-sm font-medium text-slate-900">{user.nome}</p>
          <p className="mb-2 text-xs text-slate-500">{PERFIL[user.perfil]}</p>
          <button className="btn-ghost w-full" onClick={sair}>
            <LogOut className="h-4 w-4" />
            Sair
          </button>
        </div>
      </aside>

      {/* Barra superior (celular) */}
      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur md:hidden">
        {marca}
        <button className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-900" onClick={sair} aria-label="Sair">
          <LogOut className="h-5 w-5" />
        </button>
      </header>

      <main className="mx-auto max-w-4xl px-4 pb-24 pt-5 md:ml-60 md:max-w-none md:px-8 md:pb-10 md:pt-8">
        <div className="mx-auto max-w-4xl">{children}</div>
      </main>

      {/* Navegação inferior (celular) */}
      <nav className="fixed inset-x-0 bottom-0 z-20 flex overflow-x-auto border-t border-slate-200 bg-white/95 backdrop-blur md:hidden">
        {items.map((i) => {
          const Icon = i.icon;
          const on = ativo(i.href);
          return (
            <Link
              key={i.href}
              href={i.href}
              className={`flex min-w-[4.5rem] flex-1 shrink-0 flex-col items-center gap-1 border-t-2 px-2 py-2 text-[11px] ${
                on ? "border-slate-900 font-medium text-slate-900" : "border-transparent text-slate-500"
              }`}
            >
              <Icon className="h-5 w-5" />
              {i.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}