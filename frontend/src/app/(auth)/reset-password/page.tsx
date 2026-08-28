import type { Metadata } from "next";
import Link from "next/link";

import { AuthShell } from "@/components/ui/auth-shell";
import { ResetPasswordForm } from "@/features/auth/reset-password-form";

export const metadata: Metadata = {
  title: "Restablecer contraseña — Socratia",
  referrer: "no-referrer",
};

type ResetPasswordPageProps = {
  searchParams: Promise<{ token?: string | string[] }>;
};

export default async function ResetPasswordPage({ searchParams }: ResetPasswordPageProps) {
  const params = await searchParams;
  const token = typeof params.token === "string" ? params.token : "";
  return (
    <AuthShell
      eyebrow="Enlace seguro"
      title="Elige una nueva contraseña"
      description="Usa una frase larga y memorable que no hayas utilizado antes."
      footer={<p><Link href="/forgot-password">Solicitar otro enlace</Link></p>}
    >
      <ResetPasswordForm token={token} />
    </AuthShell>
  );
}
