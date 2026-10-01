"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Loading } from "@/components/StateViews";
import { useAuth } from "@/lib/auth";
import { homePorPerfil } from "@/lib/types";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!loading) router.replace(user ? homePorPerfil[user.perfil] : "/login");
  }, [user, loading, router]);
  return <Loading />;
}
