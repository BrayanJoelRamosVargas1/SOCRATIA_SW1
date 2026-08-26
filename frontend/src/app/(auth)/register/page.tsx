import Link from "next/link";

import { AuthShell } from "@/components/ui/auth-shell";
import { RegisterForm } from "@/features/auth/register-form";

export default function RegisterPage() {
  return (
    <AuthShell
      eyebrow="Tu primera práctica empieza aquí"
      title="Crea tu espacio en Socratia"
      description="Una cuenta segura para organizar tu preparación y seguir tu progreso."
      footer={<p>¿Ya tienes cuenta? <Link href="/login">Inicia sesión</Link></p>}
    >
      <RegisterForm />
    </AuthShell>
  );
}

