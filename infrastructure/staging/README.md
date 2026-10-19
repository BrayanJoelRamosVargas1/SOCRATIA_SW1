# Piloto privado de Socratia

Estado al 2026-10-18: fuentes y configuración transferidas a EC2; construcción
iniciada en el servidor. La publicación todavía requiere confirmar arranque,
certificado HTTPS y pruebas completas. Ver `docs/staging-readiness.md` para la
evidencia y los pendientes actuales; los costes y la factura histórica de abajo
no representan el consumo actual.

## Preparación

1. Ejecutar `python infrastructure/scripts/init_staging_env.py --domain pruebas.example.com`.
2. Completar las claves de proveedores en `.env.staging` directamente en el servidor. No subir este archivo a Git.
3. Apuntar el DNS al servidor y permitir HTTP/HTTPS. Caddy obtiene el certificado; cámara y micrófono requieren HTTPS.
4. Ejecutar `STAGING_ENV_FILE=.env.staging docker compose --env-file .env.staging -f compose.staging.yaml up -d --build`.
5. Crear cuentas mediante `docker compose --env-file .env.staging -f compose.staging.yaml exec backend python -m app.cli.create_trial_user --help`; la contraseña se introduce de forma interactiva.

La base de datos y el backend no publican puertos. Hay volúmenes persistentes para documentos, PostgreSQL y TLS. Borrar volúmenes elimina datos: no usar `down -v` sobre un piloto con información que deba conservarse.

## Consumo y límites

El perfil de ejemplo cierra el registro público, desactiva TTS de pago y la revisión automática de vestimenta, usa pgvector local y reduce contexto y reintentos de evaluación. Estas medidas reducen consumo, pero NO constituyen un límite monetario. Las APIs de Gemini/Groq facturan fuera de AWS.

`python infrastructure/scripts/estimate_trial_cost.py` calcula un escenario, no mide tokens reales. Con sus supuestos de 100 sesiones, 100 documentos nuevos, 12 respuestas, 20 minutos de audio y 3 revisiones de ropa por sesión, estima US$5,65 de IA más US$24 hipotéticos de alojamiento: US$29,65 antes de extras. No es una oferta, una garantía de capacidad ni un presupuesto autorizado. Ese supuesto de alojamiento no representa la factura de la instancia EC2 actualmente publicada. Consultar las fuentes y exclusiones incluidas en la salida del script.

Los planes actuales declaran 2/10/50 documentos, 3/30/100 simulaciones y 25/150/500 MB. La revisión del código encontró que esos cupos todavía no se aplican en los servicios de creación de documentos y simulaciones. No abrir un piloto público ni presentar esos límites como protección de gasto hasta implementarlos y probar concurrencia, periodos y cancelaciones. No existe todavía medición persistente completa de tokens por sesión.

El piloto de una sola máquina no proporciona alta disponibilidad. El piloto usa un nombre HTTPS ligado a su IP pública. Siguen pendientes restauración de copias, pruebas de concurrencia y el recorrido completo de defensa con cámara física, audio y evaluación real en AWS. Las cuentas nuevas de alumno y administrador sí fueron verificadas. Dos avatares de demostración requieren revisar/sustituir sus licencias antes de uso comercial.

## Verificación realizada

- Imágenes de backend y frontend construidas; frontend actualizado a Next 16.4.1 y compilación de TypeScript correcta.
- `npm audit --omit=dev`: cero vulnerabilidades reportadas; permanecen cinco avisos altos en dependencias de desarrollo de ESLint (no se aplicó una bajada incompatible de versión).
- Base nueva con migraciones y backend saludables; `/health` del backend y `/login` del frontend devolvieron HTTP 200 desde la red interna de contenedores.
- Pruebas de controles de consumo, vestimenta, voz y cancelación: 38 pruebas aprobadas en la preparación previa. No se hicieron llamadas pagadas nuevas para esta verificación de contenedores.

## AWS y créditos

La cuenta observada está en Free account plan. No actualizar a Paid ni crear/juntar Organizations o Control Tower: pueden cambiar las condiciones del plan. La factura de octubre observada mostraba US$0 a pagar y US$5,98 de uso cubierto por créditos. El saldo no equivale a dinero disponible para proveedores externos.

UML Case Tool (`uml-case-demo`) fue terminada con confirmación expresa; su disco raíz de 20 GiB desapareció del inventario. Las cinco promociones EC2, Budgets, Bedrock, Lambda y RDS figuran completadas: US$100 ganados. Lambda, su rol y su grupo de registros fueron eliminados. La base vacía `socratia-promo-rds-temporal` también fue eliminada con confirmación expresa, sin instantánea final ni copias automáticas conservadas; AWS confirmó la eliminación y el inventario de bases quedó vacío. La alerta `Socratia - alerta gasto cero` incluye aviso desde US$0,01 y necesita verificar el correo del destinatario. Budgets avisa; no corta recursos automáticamente.

La documentación de planes indica que Free account plan no admite otros créditos promocionales o descuentos. AWS Activate Founders anuncia US$1.000 para startups elegibles (autofinanciadas, nuevas en Activate, sitio empresarial funcional, fundadas en los últimos diez años), pero eso no demuestra elegibilidad de Socratia ni compatibilidad con el plan gratuito actual. No se envió una solicitud ni se cambió el plan. AWS Educate actualmente ofrece formación y laboratorios gratuitos; los anuncios antiguos de 2015 sobre créditos no prueban que se acrediten fondos a esta cuenta hoy.

Fuentes oficiales: https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans-activities.html y https://docs.aws.amazon.com/us_en/awsaccountbilling/latest/aboutv2/free-tier.html .
