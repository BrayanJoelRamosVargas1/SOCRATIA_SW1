import Link from "next/link";

import { AuthShell } from "@/components/ui/auth-shell";

export default function ForgotPasswordPage() {
  return (
    <AuthShell
      eyebrow="Recuperación de acceso"
      title="Este flujo llega en el próximo incremento"
      description="La recuperación por correo requiere integrar un proveedor transaccional. Por ahora, el equipo puede gestionar el acceso desde la base local."
      footer={<p><Link href="/login">Volver a iniciar sesión</Link></p>}
    >
      <div className="notice-card"><strong>Decisión consciente</strong><p>No simulamos un correo que todavía no se envía. El contrato se implementará junto con notificaciones.</p></div>
    </AuthShell>
  );
}

