"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { LayoutDashboard, Files, Mic, ChartNoAxesCombined, UserRound, CreditCard, ShieldCheck, Menu, PanelLeftClose, X, ArrowUpRight } from "lucide-react";
import type { User } from "@/types/user";
import { Logo } from "@/components/ui/logo";
import { LogoutButton } from "@/features/auth/logout-button";
import { apiRequest } from "@/lib/api";
import { warmNavigation } from "@/lib/navigation-prefetch";

type AppSidebarProps = { user?: User | null; active: "dashboard" | "documents" | "simulations" | "profile" | "subscription" | "history" };
const links = [
  { href: "/dashboard", key: "dashboard", label: "Mi preparación", icon: LayoutDashboard },
  { href: "/documents", key: "documents", label: "Documentos", icon: Files },
  { href: "/simulations", key: "simulations", label: "Simulaciones", icon: Mic },
  { href: "/history", key: "history", label: "Resultados", icon: ChartNoAxesCombined },
  { href: "/profile", key: "profile", label: "Mi perfil", icon: UserRound },
  { href: "/subscription", key: "subscription", label: "Suscripción", icon: CreditCard },
];

function subscribeMobile(onChange: () => void) {
  const query = window.matchMedia("(max-width: 980px)");
  query.addEventListener("change",onChange);
  return () => query.removeEventListener("change",onChange);
}
export function AppSidebar({ user, active }: AppSidebarProps) {
  const isMobile = useSyncExternalStore(subscribeMobile,() => window.matchMedia("(max-width: 980px)").matches,() => false);
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [plan, setPlan] = useState("Consultando plan…");
  const drawer = useRef<HTMLDivElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);
  const isAdmin = user?.roles.some((role) => ["administrator", "admin"].includes(role.toLowerCase()));

  useEffect(() => {
    if(!user?.id)return;
    let cancelled = false;
    apiRequest<{ subscription: { status: string } | null; plan: { name: string } | null }>("/subscription")
      .then((data) => { if (!cancelled) setPlan(data.plan?.name ?? "Sin suscripción activa"); })
      .catch(() => { if (!cancelled) setPlan("Plan no disponible"); });
    return () => { cancelled = true; };
  }, [user?.id]);

  useEffect(() => {
    const layout = toggle.current?.closest(".dashboard-layout");
    layout?.classList.toggle("sidebar-collapsed", collapsed);
    return () => { layout?.classList.remove("sidebar-collapsed"); };
  }, [collapsed]);

  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    drawer.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
      if (event.key !== "Tab") return;
      const items = drawer.current?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])');
      if (!items?.length) return;
      const first = items[0], last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    const onResize = () => { if (window.innerWidth > 980) setOpen(false); };
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", onResize);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onResize);
      previousFocus?.focus();
    };
  }, [open]);

  const navigation = (compact = false) => <nav className="workspace-nav" aria-label="Navegación principal">
    {links.map(({ icon: Icon, ...item }) => <Link key={item.key} href={item.href} onPointerEnter={()=>warmNavigation(item.href)} onFocus={()=>warmNavigation(item.href)} title={item.label} aria-current={active === item.key ? "page" : undefined} className={`nav-item ${active === item.key ? "active" : ""} ${compact ? "collapsed" : ""}`} onClick={() => setOpen(false)}><Icon size={19} aria-hidden="true" />{!compact && <span>{item.label}</span>}</Link>)}
    {isAdmin && <Link href="/admin/dashboard" className={`nav-item ${compact ? "collapsed" : ""}`} title="Administración" onClick={() => setOpen(false)}><ShieldCheck size={19} aria-hidden="true" />{!compact && <span>Administración</span>}</Link>}
  </nav>;
  const profile = <Link href="/profile" className="workspace-profile" onClick={() => setOpen(false)}><span className="workspace-avatar">{user?.full_name?.slice(0, 1).toUpperCase() || "S"}</span><span><strong>{user?.full_name || "Tu espacio"}</strong><small>{isAdmin ? "Administrador" : "Preparación académica"}</small></span></Link>;

  return <>
    <aside className={`dashboard-sidebar workspace-sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="sidebar-brand-row">{(!collapsed || isMobile) && <Logo />}<button ref={toggle} className="hamburger-btn" type="button" aria-label="Abrir o contraer navegación" aria-expanded={isMobile ? open : !collapsed} aria-controls="workspace-mobile-menu" onClick={() => window.innerWidth <= 980 ? setOpen(!open) : setCollapsed(!collapsed)}>{collapsed ? <Menu size={20} /> : <PanelLeftClose size={20} />}</button></div>
      <div className="workspace-desktop">{!collapsed && <><p className="workspace-caption">ESPACIO PERSONAL</p>{profile}</>}{navigation(collapsed)}
        {!collapsed && <div className="workspace-plan"><CreditCard size={20} /><strong>{plan}</strong><p>Consulta tu acceso y las opciones de tu plan.</p><Link href="/subscription">Ver mi suscripción <ArrowUpRight size={15} /></Link></div>}
        <div className="workspace-footer"><LogoutButton className={collapsed ? "compact-logout" : "desktop-logout"} /></div>
      </div>
    </aside>
    {open && <><div className="sidebar-backdrop" onClick={() => setOpen(false)} aria-hidden="true" /><div ref={drawer} id="workspace-mobile-menu" className="sidebar-mobile-drawer" role="dialog" aria-modal="true" aria-label="Menú principal"><div className="drawer-header"><Logo /><button type="button" className="hamburger-btn" aria-label="Cerrar menú" onClick={() => setOpen(false)}><X size={20} /></button></div>{profile}{navigation()}<div className="workspace-footer"><LogoutButton /></div></div></>}
  </>;
}
