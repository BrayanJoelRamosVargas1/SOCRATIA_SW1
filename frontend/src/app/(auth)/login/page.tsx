import Link from "next/link";

import { AuthShell } from "@/components/ui/auth-shell";
import { LoginForm } from "@/features/auth/login-form";

export default function LoginPage() {
  return (
    <AuthShell
      eyebrow="Bienvenido de vuelta"
      title="Continúa tu preparación"
      description="Ingresa con la cuenta que usarás durante tus prácticas."
      footer={<p>¿Aún no tienes cuenta? <Link href="/register">Créala gratis</Link></p>}
    >
      <LoginForm />
    </AuthShell>
  );
}

