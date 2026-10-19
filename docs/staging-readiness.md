# Preparación del piloto — 18 de octubre de 2026

Se recuperó la sesión de AWS y se accedió por EC2 Instance Connect a
`socratia-staging` (`i-0c8f0a2f4ce418b0b`), en ejecución con 3/3 comprobaciones
aprobadas y dirección `34.204.9.87`. Se verificaron aproximadamente 1,4 GB de
memoria disponible, 2 GB de swap y 13 GB libres de disco. Docker y Compose están
instalados; inicialmente no había contenedores ni aplicación instalada.

El paquete de fuentes de 89.138.752 bytes se transfirió y verificó en EC2 con
SHA-256 `4b27ab66dc65c19705754164df7d95d209506d3d287f70d6cae3db3dc95b2273`.
La configuración privada se transfirió por separado, con secretos nuevos y claves
de proveedores existentes, sin incorporarla al paquete de fuentes ni a Git.
La transferencia pasó por CloudShell y el bucket privado
`socratia-deploy-870900716266-us-east-1`, con los cuatro bloqueos de acceso público
activados y cifrado AES256 del objeto. Permanece una copia privada de transferencia
con configuración: tratarla como secreto; no publicar ni compartir ese objeto.

Se inició construcción secuencial en EC2, con heap de Node limitado a 1024 MB,
registro `/opt/socratia/deploy.log`. Todavía falta confirmar su resultado y la
publicación HTTPS; iniciar una construcción no demuestra que el sistema funcione.
Nombre de prueba preparado: `socratia.34.204.9.87.sslip.io`, resuelve a la IP
actual. Su uso depende de DNS externo y cambiará si cambia la IP de EC2.

## Preparado y comprobado

- Despliegue con PostgreSQL/pgvector, backend, frontend y Caddy para HTTPS.
- Backend y base sin puertos públicos; secretos separados del paquete.
- Contextos Docker excluyen `.env` y sus variantes, además de entornos locales.
- Registro público cerrado y voz de pago desactivada en el perfil del piloto.
- 42 pruebas de defensa aprobadas en la validación anterior, incluyendo voz,
  cancelación y cierre; transcripción real WAV/WebM con Groq y Gemini comprobada.
- Seis escenarios visuales sintéticos con modelos reales aprobados. No equivalen
  a comprobar una cámara física, iluminación real o prendas reales.
- Comprobador externo de solo lectura, sin llamadas de IA:

  ```sh
  python infrastructure/scripts/check_staging_http.py --url https://DOMINIO --output staging-http.json
  ```

  Comprueba certificado HTTPS, backend JSON, página de ingreso y rechazo del
  perfil sin autenticación. Cuatro pruebas de regresión del comprobador pasan.
  No sustituye una prueba de base, documentos o WebSocket.

## Pendientes para publicar

1. Recuperar sesión AWS y verificar estado, almacenamiento y acceso del servidor
   previamente autorizado. No dar por vigentes su IP ni saldo históricos.
2. Resolver nombre HTTPS y apuntarlo a la IP actual. Con HTTP público sin TLS
   no se podrá validar correctamente cámara/micrófono en los navegadores.
3. Configurar claves en el servidor, generar secretos nuevos y ejecutar las
   migraciones. No copiar la base ni contraseñas de la validación local.
4. Construir fuera de la laptop. Medir memoria/disco antes de construir en la
   t3.small: no está demostrado que la compilación y todos los servicios quepan
   a la vez. No activar modelos locales pesados ni aumentar instancia sin medir.
5. Crear cuentas de alumno y administrador; verificar aislamiento entre alumnos
   y acciones del administrador. Establecer copia y restauración antes de cargar
   documentos que se quieran conservar.
6. Elegir y comprobar la voz del servidor. Con TTS de pago desactivado puede
   usarse la voz del navegador; eso no garantiza video humano sincronizado.

## Pruebas duras, en el servidor

Primero ejecutar el comprobador HTTPS y una defensa completa real: subir un
documento ficticio, generar preguntas, responder por voz, interrumpir al jurado,
recargar, reconectar y terminar con informe. Comprobar cámara física, ausencia,
mirada lateral, encuadre insuficiente y prendas; mostrar «no verificable» cuando
falte evidencia. No mostrar inferencias como certezas.

Después avanzar de 1 a 2 y 5 sesiones simultáneas con usuarios independientes.
Medir latencias, errores, reinicios, CPU, memoria, disco y número de llamadas de
IA. Separar carga de infraestructura de llamadas reales a proveedores para no
gastar en una prueba masiva accidental. Detener el incremento al aparecer
errores persistentes, memoria agotada o reinicios; no prometer capacidad antes.

Los cupos anunciados por los planes y la medición persistente de tokens siguen
pendientes de una validación completa. Mantener el acceso por invitación; no
abrir registro público como si hubiera un tope monetario. AWS y las APIs externas
tienen consumos separados. Una alerta de AWS no apaga automáticamente recursos.

## Verificación pública confirmada

Se confirmó el piloto en https://socratia.34.204.9.87.sslip.io/login . Los cuatro
contenedores llevan aproximadamente 46 minutos activos; backend y PostgreSQL
reportan estado saludable. La comprobación externa devuelve `/health` 200,
`/login` 200 y `/api/v1/profile` 401 sin autenticación, con HTTPS válido.
Resultado en `artifacts/staging-http-20261018.json` y captura en
`docs/screenshots/staging-live-login.png`.

La base contiene `alumno.socratia@example.com` con rol `student` y
`admin.socratia@example.com` con rol `admin`. El archivo `.trial-access.json`
está vacío: no se recuperaron contraseñas ni se modificaron las existentes.
No se ha validado todavía el ingreso de esas cuentas ni una defensa real en
este servidor. Las pruebas de concurrencia y restauración siguen pendientes.
