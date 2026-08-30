import type { User } from "@/types/user";
import Link from "next/link";

import { Logo } from "@/components/ui/logo";
import { LogoutButton } from "@/features/auth/logout-button";

type AppSidebarProps = {
  user: User;
  active: "dashboard" | "documents" | "simulations";
};

export function AppSidebar({ user, active }: AppSidebarProps) {
  const firstName = user.full_name.split(" ")[0];
  return (
    <aside className="dashboard-sidebar">
      <Logo />
      <nav aria-label="Navegación principal">
        <Link className={`nav-item ${active === "dashboard" ? "active" : ""}`} href="/dashboard">
          Resumen
        </Link>
        <Link className={`nav-item ${active === "documents" ? "active" : ""}`} href="/documents">
          Documentos
        </Link>
        <Link className={`nav-item ${active === "simulations" ? "active" : ""}`} href="/simulations">
          Simulaciones
        </Link>
        <span className="nav-item disabled">Reportes <small>Próximo</small></span>
      </nav>
      <div className="sidebar-user">
        <span className="avatar">{firstName.slice(0, 1).toUpperCase()}</span>
        <div><strong>{user.full_name}</strong><small>{user.email}</small></div>
      </div>
      <LogoutButton />
    </aside>
  );
}
