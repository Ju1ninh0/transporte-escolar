"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import type { Perfil } from "@/lib/types";

type Item = { href: string; icon: string; label: string; soon?: boolean };

const MENU: Record<Perfil, Item[]> = {
  RESPONSAVEL: [
    { href: "/responsavel", icon: "🏠", label: "Início" },
    { href: "#", icon: "📍", label: "Van", soon: true },
    { href: "#", icon: "📅", label: "Frequência", soon: true },
    { href: "#", icon: "💰", label: "Financeiro", soon: true },
    { href: "#", icon: "⚠️", label: "Ocorrências", soon: true },
  ],
  MOTORISTA: [{ href: "/motorista", icon: "🏠", label: "Início" }],
  ADMIN: [
    { href: "/admin", icon: "📊", label: "Painel" },
    { href: "/admin/alunos", icon: "🎒", label: "Alunos" },
    { href: "/admin/responsaveis", icon: "👪", label: "Responsáveis" },
  ],
};

export function Shell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const path = usePathname();
  const router = useRouter();
  if (!user) return null;
  const items = MENU[user.perfil];

  const link = (it: Item, cls: string) =>
    it.soon ? (
      <span key={it.label} className={`${cls} opacity-40`} title="Em breve">
        <span>{it.icon}</span>
        <span>{it.label}</span>
      </span>
    ) : (
      <Link
        key={it.label}
        href={it.href}
        className={`${cls} ${path === it.href ? "font-bold text-emerald-700" : "text-slate-600"}`}
      >
        <span>{it.icon}</span>
        <span>{it.label}</span>
      </Link>
    );

  return (
    <div className="min-h-screen bg-slate-50 pb-20 md:pb-0">
      <header className="sticky top-0 z-10 border-b bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <span className="font-bold text-emerald-700">🚐 Transporte Escolar</span>
          <nav className="hidden gap-5 md:flex">{items.map((i) => link(i, "flex items-center gap-1"))}</nav>
          <button
            className="btn-ghost"
            onClick={async () => {
              await logout();
              router.replace("/login");
            }}
          >
            Sair
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-5xl p-4">{children}</main>
      <nav className="fixed inset-x-0 bottom-0 flex justify-around border-t bg-white py-2 text-xs md:hidden">
        {items.map((i) => link(i, "flex flex-col items-center gap-0.5 px-2"))}
      </nav>
    </div>
  );
}
