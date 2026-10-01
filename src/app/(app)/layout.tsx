"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Loading } from "@/components/StateViews";
import { Shell } from "@/components/Shell";
import { useAuth } from "@/lib/auth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);
  if (!user) return <Loading />;
  return <Shell>{children}</Shell>;
}
