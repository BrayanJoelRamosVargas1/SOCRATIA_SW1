"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Users, Layers, CreditCard, SlidersHorizontal, Scale, ArrowUpRight, ShieldCheck } from "lucide-react";
import { Logo } from "@/components/ui/logo";
const links = [
  { href: "/admin/dashboard", label: "Resumen", icon: LayoutDashboard },
  { href: "/admin/users", label: "Usuarios", icon: Users },
  { href: "/admin/plans", label: "Planes", icon: Layers },
  { href: "/admin/subscriptions", label: "Suscripciones", icon: CreditCard },
  { href: "/admin/ai-settings", label: "Configuración IA", icon: SlidersHorizontal },
  { href: "/admin/jury-profiles", label: "Jurados", icon: Scale },
];
export function AdminNav() {
  const pathname = usePathname();
  return <header className="admin-navigation"><div className="admin-brand"><Logo /><span className="admin-label"><ShieldCheck size={14} /> Administración</span><Link href="/dashboard" className="admin-return">Mi preparación <ArrowUpRight size={16} /></Link></div><nav aria-label="Administración" className="admin-tabs">{links.map(({icon: Icon, ...item}) => <Link key={item.href} href={item.href} aria-current={pathname.startsWith(item.href) ? "page" : undefined}><Icon size={17} aria-hidden="true" />{item.label}</Link>)}</nav></header>;
}
