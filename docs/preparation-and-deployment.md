# Preparación persistente y vínculo Git → EC2

## Cola sin servicios externos adicionales

Las rutas `POST /documents/{id}/tasks` y `GET /documents/{id}/tasks` guardan metadatos
por propietario en PostgreSQL. Admiten procesamiento, preguntas y presentaciones.
La clave de solicitud evita repetir una solicitud ya completada y un bloqueo del
documento, más un índice único parcial, evita dos preparaciones activas sobre él.
Estados: QUEUED, RUNNING, SUCCEEDED, FAILED, INTERRUPTED. No se inventan porcentajes.
Las duraciones son tiempos observados de cada tarea, no una predicción.

Un proceso dedicado `preparation-worker` comparte la imagen backend y los archivos,
con una sola tarea a la vez. No añade Redis, GPU ni un modelo local. Al reiniciar,
retoma las tareas que seguían en cola; una tarea interrumpida durante una llamada
externa se marca para revisión y no se repite automáticamente. Esta decisión evita
confundir una respuesta perdida con una llamada no consumida. El resultado se
consulta desde los materiales del documento, incluso después de cerrar la pestaña.
Las rutas síncronas antiguas se conservan por compatibilidad; el detalle web usa
la cola nueva. No deben usarse ambos mecanismos simultáneamente para el mismo PDF.

La evaluación final guarda cada respuesta evaluada antes de continuar. Si una
cuota falla después, el reintento reutiliza esas filas y evalúa solo las pendientes.
Esto reduce repetición de consumo, pero no elimina los límites por minuto/día ni
valida precisión de la IA. No existe todavía un contador monetario completo por
sesión ni un cortacircuito financiero compartido entre todos los proveedores.

## Publicación desde main

El repositorio público se consulta con acceso de lectura anónimo. No se guardan
claves de GitHub ni de AWS en el controlador. El controlador estable se instala
fuera del checkout, en `/opt/socratia-deployment/deploy-main.sh`; su unidad systemd
consulta main cada cinco minutos, sin builds cuando el commit no cambió. Las ramas
secundarias no despliegan. Solo admite avances de historial, no force pushes.

La publicación bloquea ejecuciones simultáneas, crea un pg_dump comprimido en el
disco cifrado existente, conserva etiquetas de imágenes anteriores, construye en
EC2 y comprueba salud/HTTPS antes de registrar el commit publicado. Un commit que
falló no se vuelve a construir en cada consulta: revisar el journal y reparar o
publicar un commit nuevo. Las migraciones no se revierten automáticamente; un
fallo de migración requiere revisar su estado y el respaldo. El disco compartido
no constituye una copia externa ante pérdida de EC2.

Operación en EC2:

- Estado: `systemctl status socratia-deploy.timer`.
- Registro: `journalctl -u socratia-deploy.service -n 60`.
- Versión: `/opt/socratia/RELEASE.json` y
  `/opt/socratia-deployment/deployed-commit`.
- Pausar publicaciones: `sudo systemctl stop socratia-deploy.timer`.
- Publicar ahora: `sudo systemctl start socratia-deploy.service`.

Las claves, uploads, base y volúmenes no se toman de Git. No ejecutar `down -v`.
Los scripts de control no se sustituyen a sí mismos durante una publicación;
cambios en el controlador requieren reinstalarlo expresamente. Los respaldos
locales deben supervisarse para no llenar el disco y exportarse de forma privada
antes de la presentación. El timer consulta Git; no es un GitHub runner ni un
servicio AWS de despliegue facturable nuevo.

## Validación pendiente

Falta el ensayo de restauración en un servidor aislado, medir p50/p95 con defensas
reales de 1/2/5 usuarios y contrastar cámara física. Estas mejoras no se declaran
terminadas por el hecho de pasar pruebas con proveedores simulados. Las cuotas
específicas de Gemini y Groq necesitan la sesión del propietario del proyecto.
