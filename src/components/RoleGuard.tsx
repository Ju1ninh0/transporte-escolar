"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Loading } from "@/components/StateViews";
import { useAuth } from "@/lib/auth";
import { homePorPerfil, type Perfil } from "@/lib/types";

export function RoleGuard({ perfil, children }: { perfil: Perfil; children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const ok = !loading && user?.perfil === perfil;

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
    } else if (user.perfil !== perfil) {
      router.replace(homePorPerfil[user.perfil]);
    }
  }, [loading, user, perfil, router]);

  return ok ? <>{children}</> : <Loading />;
}