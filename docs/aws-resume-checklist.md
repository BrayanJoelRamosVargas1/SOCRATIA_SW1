# Reanudar el piloto sin perder datos

La última instancia conocida es `i-0c8f0a2f4ce418b0b`, cuenta `870900716266`, región `us-east-1`. Confirmar esos datos en AWS antes de actuar. No actualizar el plan ni crear servicios de pago adicionales para arrancar el piloto.

## Antes de habilitar pruebas

1. Revisar saldo y cargos estimados. Arrancar la instancia existente; no crear otra ni eliminar volúmenes.
2. Leer su IPv4 pública actual. Una dirección automática puede cambiar tras detenerla. El enlace antiguo no constituye una dirección permanente.
3. Si cambió, corregir `PUBLIC_DOMAIN` en `/opt/socratia/.env.staging` al nombre sslip.io correspondiente. Conservar claves, contraseñas, volúmenes y las demás variables. Revisar posibles valores explícitos de `CORS_ORIGINS` y `FRONTEND_URL` en ese archivo; Compose establece ambos desde `PUBLIC_DOMAIN` para el backend.
4. Mantener el frontend con `NEXT_PUBLIC_API_URL=/api/v1`. No incrustar la IP antigua en una compilación nueva.
5. Tras obtener los últimos cambios de `main`, instalar también el controlador actualizado: el script operativo está en `/opt/socratia-deployment/deploy-main.sh`, separado de la copia del repositorio `/opt/socratia/infrastructure/staging/deploy-main.sh`. Confirmar su ruta en la unidad systemd antes de reemplazarlo. El controlador actualizado verifica HTTPS usando el dominio configurado, no una IP fija.
6. Ejecutar el despliegue existente y verificar su salida y `RELEASE.json`. Si quedó un `failed-commit`, revisar primero el fallo y el respaldo antes de habilitar otro intento. No borrar ese marcador a ciegas.
7. Confirmar `/health`, `/login`, HTTPS válido, acceso de ambos roles y autorización del WebSocket con el nuevo dominio. Probar documento ficticio, descarga de presentación y una respuesta con voz; comprobar cámara física y audio en los dispositivos que usará el equipo. Estas últimas comprobaciones requieren el servidor encendido y permisos del usuario.

## Respaldo y recuperación

El controlador genera `backups/pre-deploy-*.sql.gz` en el disco del servidor. **Eso no es un respaldo fuera de la instancia.** Git conserva código; no conserva las cargas de los usuarios ni las variables secretas.

Antes de eliminar infraestructura o datos, exportar y descargar por una conexión segura:

- Un volcado PostgreSQL consistente, comprobado con `gzip -t` y restaurado en una base aislada.
- Los archivos del volumen `staging_documents`, conservando sus rutas.
- La configuración `.env.staging`, mediante un medio privado y con acceso restringido; nunca Git, capturas ni mensajes del chat.

Comprobar el recorrido de restauración con un documento ficticio antes de confiar en la copia. No usar `docker compose down -v`. No se han creado buckets, copias externas ni recursos adicionales automáticamente.

## Condiciones del piloto

La suite automática usa proveedores simulados. No certifica cámara física, cuotas disponibles ni disponibilidad del proveedor. No presentar una promesa de funcionamiento al 100 % sin la verificación real anterior. Para detener el consumo de cómputo, parar la instancia; EBS sigue generando almacenamiento. Una IP elástica nueva tendría costo y no se requiere para estas instrucciones.
