import Link from "next/link";

import { AuthShell } from "@/components/ui/auth-shell";
import { ForgotPasswordForm } from "@/features/auth/forgot-password-form";

export default function ForgotPasswordPage() {
  return (
    <AuthShell
      eyebrow="Recuperación de acceso"
      title="Recupera el acceso a tu cuenta"
      description="Te enviaremos un enlace seguro para que elijas una nueva contraseña."
      footer={<p><Link href="/login">Volver a iniciar sesión</Link></p>}
    >
      <ForgotPasswordForm />
    </AuthShell>
  );
}
