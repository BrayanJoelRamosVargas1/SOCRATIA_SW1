import type { Metadata } from "next";
import { AdminAccess } from "@/components/admin/admin-access";
import { AdminNav } from "@/components/admin/admin-nav";
import { ProductGuide } from "@/components/product-guide";

export const metadata: Metadata = {
  title: "Administración | Socratia",
  description: "Gestiona usuarios, planes, jurados y configuración de Socratia",
};

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AdminAccess><div className="admin-workspace min-h-screen bg-slate-50 text-slate-900">
      <AdminNav />
      <ProductGuide />
      <main className="pb-16">{children}</main>
    </div></AdminAccess>
  );
}
