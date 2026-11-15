# Revisión del sistema — 15 de noviembre de 2026

Alcance: revisión de código de autenticación, simulación por WebSocket, preparación de documentos, evaluación, cliente HTTP y despliegue. Pruebas locales con PostgreSQL desechable y proveedores simulados. No se encendió AWS ni se utilizaron cuotas externas. Esta revisión no sustituye una prueba de carga ni una auditoría de seguridad completa.

## Correcciones de esta revisión

| Prioridad | Hallazgo | Cambio |
|---|---|---|
| Alta | La salida estructurada de evaluación aceptaba notas negativas, mayores que 100 o no finitas. Podían contaminar el promedio o impedir serializar el reporte. | Límites de 0–100 y rechazo explícito de NaN e infinito antes de guardar. |
| Media | El trabajador de preparación no manejaba SIGTERM. Un despliegue esperaba hasta 180 segundos y después podía matar el proceso. | Apagado cooperativo: termina la tarea activa, no toma otra e interrumpe la espera cuando está inactivo. Se conserva el límite externo para tareas bloqueadas. |
| Baja | Errores de voz, origen WebSocket y cierre de simulación todavía tenían mensajes en inglés. | Mensajes visibles en español, sin cambiar códigos del protocolo. |

## Pendientes y riesgos encontrados en código

1. **Evaluaciones concurrentes (alta).** La comprobación de estado y la creación de evaluación no están serializadas por simulación. La restricción única evita duplicar filas, pero no es una garantía de una sola llamada al proveedor cuando dos solicitudes reintentan una evaluación fallida. Requiere prueba concurrente y adquisición atómica antes de consumir cuota.
2. **Revocación en conexiones WebSocket existentes (alta).** La identidad se valida al conectar; no se vuelve a comprobar su versión o estado en cada operación. Debe probarse el caso de desactivar un usuario durante una defensa y definir la renovación de acceso sin cortar respuestas válidas.
3. **Detección de idioma (media, reproducida).** El detector confunde algunos textos españoles sin tildes con otros idiomas. Dos alertas de la auditoría anterior eran falsos positivos, no diapositivas en inglés. Requiere un conjunto de ejemplos etiquetados y ajuste de umbrales antes de ampliar su uso como bloqueo.
4. **Listados sin paginar (media).** El listado de documentos carga todos los del propietario. Con los pocos usuarios del piloto el impacto es limitado; con muchos documentos debe paginarse coordinando la API y la interfaz.
5. **Cambio de IP al volver a encender AWS (alta para disponibilidad).** La instancia usaba una IPv4 pública automática, sin IP elástica. Al arrancar puede cambiar y dejar obsoleto el dominio sslip.io anterior. Deben actualizarse dominio, Caddy, variables del frontend/backend y los controles de origen, y validar HTTPS antes de dar el enlace al equipo.
6. **Respaldo en el mismo disco (alta para recuperación).** El despliegue hace una copia PostgreSQL local, pero no protege ante pérdida del volumen. Antes de eliminar infraestructura hace falta exportar y comprobar base de datos y archivos; Git contiene código, no los datos de uso ni secretos.
7. **Recursos y carga real (media).** El piloto tiene una t3.small de 2 GB. La voz CPU, el procesamiento de documentos y las compilaciones comparten recursos. Faltan mediciones de memoria, latencia p95 y cola con dos defensas simultáneas. No se ejecutó carga pesada en la laptop.

## Validación

La suite `release` cubre integración de identidad, aislamiento por propietario, documentos, preparación, voz, suscripciones, evaluaciones y reportes. Las pruebas nuevas verifican el cierre cooperativo y el rechazo de notas inválidas. El resultado de cada ejecución se guarda fuera de Git en `artifacts/defense-validation/release-tests.xml` y `release-run.json`.

Resultado específico: 16 pruebas aprobadas de apagado del trabajador, límites de evaluación, cancelación de audio y controles de costo. Pasaron también las pruebas del cliente API, caché, subida de archivos, voces diferenciadas y control de turnos del reproductor. Las pruebas de interfaz de conversación automática y visión no llegaron a ejecutarse: localhost:3000 estaba apagado (conexión rechazada). No se consideran aprobadas ni una demostración de fallo del producto.

Resultado general: **311 pruebas aprobadas, sin fallos ni errores**, en PostgreSQL temporal. Las 16 específicas se ejecutaron además para comprobar los límites de notas incorporados durante la revisión; sus resultados no se suman al total general porque hay cobertura repetida.

## Preparación posterior para publicar

Se añadió adquisición de evaluación mediante bloqueo de la simulación y publicación de `PROCESSING` antes de llamar al proveedor; una prueba desde otra sesión comprueba que recibe 409 y no repite la llamada. El WebSocket consulta estado y versión de autenticación antes de procesar mensajes de control, para rechazar respuestas tras una revocación sin consultar por cada fragmento de audio. Las pruebas cubren usuario eliminado, inactivo y versión revocada.

El despliegue toma el dominio de la configuración efectiva de Compose y valida su formato. Se eliminó la IP fija de los controles HTTPS. El procedimiento de reanudación y respaldo está en `docs/aws-resume-checklist.md`: actualizar el controlador operativo del servidor sigue siendo necesario al volver a acceder a AWS.

Validación para publicar: **317 pruebas generales aprobadas**; después, **25 pruebas específicas `readiness` aprobadas** con el estado final del código (no se suman porque hay pruebas repetidas). Pasaron cinco scripts del cliente: API, caché, subida, voces y control del reproductor. `bash -n` aprobó el script de despliegue. No se ejecutó un build de producción en la laptop ni una comprobación de Compose contra las variables privadas de AWS.

AWS sigue detenido por instrucción del usuario; publicar código en Git no implica comprobar un servidor apagado. Permanecen pendientes la restauración de un respaldo externo, las mediciones de carga y la comprobación física de cámara/audio. No se promete funcionamiento al 100 % con esos controles pendientes.
