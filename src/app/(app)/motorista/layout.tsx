import { RoleGuard } from "@/components/RoleGuard";

export default function Layout({ children }: { children: React.ReactNode }) {
  return <RoleGuard perfil="MOTORISTA">{children}</RoleGuard>;
}
