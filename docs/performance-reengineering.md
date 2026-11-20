# Rendimiento, diapositivas y estado del despliegue

Revisión del 18 de octubre de 2026. Implementado y publicado en la instancia EC2
existente; no se añadieron servicios de pago ni modelos de inferencia al servidor.
No se ejecutó una compilación de producción en la laptop.

## Cambios publicados

- Cámara: rostro y postura se ejecutan en un Web Worker clásico del mismo origen.
  Los fotogramas se transfieren como ImageBitmap y se liberan tras cada análisis.
  Solo hay un fotograma pendiente, un máximo de cuatro análisis por segundo y
  reducción de frecuencia cuando la inferencia tarda más. Se omite trabajo con
  la pestaña oculta. La cámara solicita 15 fps, con máximo 24, a 640×480 ideal.
  Los fotogramas de seguimiento no se envían a AWS ni Colab. Vestimenta conserva
  su revisión separada mediante Gemini.
- Modelos, clips y avatares: Caddy los entrega directamente desde una carpeta
  pública de solo lectura, con caché de 24 horas. Antes tenían max-age=0. Solo los
  modelos de rostro y postura suman 9.536.342 bytes; el WASM añade unos 11,8 MB.
  El primer uso todavía debe descargarlos e inicializarlos. Los endpoints de
  documentos y usuarios no reciben esta política de caché pública.
- Documentos: banco de preguntas y presentación se consultan en paralelo. Un
  fallo de red ya no se interpreta indiscriminadamente como cierre de sesión.
- Subida: porcentaje real de transferencia mediante XMLHttpRequest, estado aparte
  de validación/guardado, mensajes de pérdida de conexión y renovación de sesión.
  No se reintenta a ciegas una subida que falla por red. El límite visible del
  piloto ahora coincide con sus 10 MB de servidor.
- Archivo: la huella SHA-256 se calcula en flujo, evitando una copia completa del
  contenido en memoria antes de guardarlo.
- Carga visual: documentos y generación muestran marcadores de estructura, con
  estado accesible. Se retiró la secuencia de mensajes que aparentaba etapas de
  IA sin medirlas. No se inventa progreso de generación.
- Presentaciones: descarga PowerPoint editable con guion en notas. Hasta tres
  imágenes raster extraíbles de las primeras diez páginas del PDF se añaden como
  anexo con su página. Se limita tamaño de imagen y miniatura. No se infiere una
  relación semántica falsa entre una figura y una diapositiva. Los gráficos
  vectoriales, PDF sin imágenes extraíbles y DOCX no producen imágenes por esta
  vía; conservan la exportación textual. No genera ilustraciones nuevas con IA.

## Comprobaciones

- 32 pruebas de documentos/presentaciones: 0 fallos, 0 errores, 0 omitidas, 35,48 s.
  Incluyen descarga PPTX y aislamiento entre propietarios. Base temporal de 32 MB,
  proveedores simulados; base detenida al terminar.
- Worker con los modelos reales y tres entradas sintéticas: frontal 1 rostro/1
  pose (262 ms de primera inferencia), mirada lateral 1/1 (62 ms), imagen vacía
  0/0 (44 ms). No equivale a validar una cámara física.
- Pruebas del cliente: no solapar capturas, transferencia del bitmap, liberación
  al desmontar, progreso de subida, renovación de sesión y fallos de red.
- TypeScript, ESLint de archivos cambiados, Ruff y dependencias Python aprobados.
- Construcción de backend y frontend y arranque saludables en AWS. Fuentes
  anteriores en `/opt/socratia/performance-backup-1792373499`; imágenes anteriores
  etiquetadas `performance-before-20261018` para recuperación.

Prueba real de nube, con un PDF ficticio de 18 KB, una sola ejecución:

| Etapa | Tiempo | Resultado |
|---|---:|---|
| Subida | 0,544 s | HTTP 201 |
| Procesamiento | 0,920 s | HTTP 200 |
| Generación con Gemini | 21,603 s | 5 diapositivas de contenido |
| Exportación/descarga | 0,817 s | PPTX de 6 diapositivas, una figura y notas |

También se verificó el enlace Descargar PowerPoint desde la interfaz real. El
archivo de prueba se conserva en `artifacts/defense-validation/defensa-ficticia-nube.pptx`.
Estos tiempos no son un SLA ni una medición de archivos grandes o concurrencia.
Los HEAD de recursos públicos están registrados antes/después en `artifacts/`;
las diferencias de una sola muestra no justifican un porcentaje global de mejora.

## Investigación y siguientes decisiones

- Google publica un ejemplo de Face Landmarker en Worker. Se adoptó ese patrón,
  manteniendo las comprobaciones de mirada y postura existentes:
  https://github.com/google-ai-edge/mediapipe-samples-web/blob/main/src/workers/face-landmarker.worker.ts
- ONNX Runtime Web admite aceleración mediante WASM/GPU. Es candidato para una
  evaluación comparativa futura, no una dependencia añadida ni una mejora medida:
  https://github.com/microsoft/onnxruntime/blob/main/js/web/README.md
- Marp exporta presentaciones, pero PDF/PPTX requiere un navegador y sus modos
  tienen diferencias de editabilidad. Para este servidor pequeño se eligió
  python-pptx sin navegador headless: https://github.com/marp-team/marp-cli y
  https://python-pptx.readthedocs.io/en/latest/api/shapes.html
- pypdf documenta extracción de imágenes incrustadas y límites de representación:
  https://pypdf.readthedocs.io/en/stable/user/extract-images.html
- Colab permite experimentos interactivos y evaluación de modelos, con recursos
  variables y restricciones sobre servicios web y otras cargas. No se conecta
  como dependencia permanente de Socratia ni se usa para sostener su API:
  https://research.google.com/colaboratory/faq.html
- Se consultaron discusiones públicas de Next.js como pistas de investigación;
  ninguna recomendación anónima se trató como evidencia de capacidad ni se copió
  código sin revisar: https://www.reddit.com/r/nextjs/comments/1jftl3d/

Falta medir una defensa completa con cámara física y archivos representativos,
latencias p50/p95 con varios usuarios, y recuperación tras cortes de red. El
procesamiento largo sigue siendo síncrono: una cola persistente con trabajos,
progreso recuperable y deduplicación es la siguiente mejora arquitectónica, pero
no se declara implementada. Agregar redes neuronales no sustituye estas mediciones;
el seguimiento ya utiliza modelos neuronales de MediaPipe.

### Actualización de preparación: 20 de noviembre de 2026

La cola persistente ya está implementada: recupera trabajos pendientes, deduplica
solicitudes y conserva resultados. No reenvía automáticamente llamadas externas
interrumpidas cuyo consumo sea incierto.

Se detectaron seis consultas de embeddings consecutivas por banco o presentación.
Ahora los seis objetivos se envían juntos al coordinador de embeddings; las
búsquedas vectoriales mantienen sus filtros por propietario y documento y se
ejecutan sobre la misma sesión, sin compartirla entre hilos. Un fallo individual
de búsqueda utiliza FTS sin descartar las demás consultas.

Para consultas interactivas, Gemini usa un intento con timeout de 10 segundos;
una cuota agotada pasa a búsqueda local sin esperar ni repetir la petición. La
indexación de documentos conserva sus reintentos. El timeout es de transporte,
no una garantía de que toda la preparación finalice en diez segundos. La
generación de texto conserva validación de español, estructura y fuentes.

Medición directa en AWS, sin regenerar ni modificar documentos de usuarios:

| Documento de origen | Construir PDF de preguntas | Construir PPTX | Leer PDF de origen |
|---|---:|---:|---:|
| 21,02 MiB | 25 ms | 245 ms | 81 ms |
| 3,40 MiB | 15 ms | 1034 ms | 14 ms |
| 2,44 MiB | 14 ms | 1114 ms | 13 ms |

Son tres muestras de construcción en el servidor, no tiempos de descarga ni
p95. Los metadatos de esos materiales registraban generación con IA de entre
19,3 y 35,0 segundos para preguntas y entre 2,7 y 25,2 para diapositivas. La
espera principal observada está en preparación/proveedores, no en escribir el
PDF. No se introduce una caché privada de exportaciones sin necesidad medida.

La consola de la cuenta AWS 870900716266 mostró US$174,10 restantes estimados y
US$25,90 utilizados estimados, con actualización aproximada cada 24 horas. El
saldo contable cerrado mostraba US$179,70: para planificar se usa la estimación
menor. Estos créditos no pagan Gemini, Groq u otros proveedores externos.

IA propia: Kokoro ONNX está integrado en el servidor para voces. Qwen se validó
en una sesión GPU de Kaggle, pero no está conectado a la generación productiva
de preguntas o diapositivas. Una sesión temporal no constituye una API estable.

Se reprodujo además un HTTP 401 al descargar PDF desde una pestaña antigua: los
enlaces directos no renovaban la sesión. PDF y PPTX ahora usan la misma renovación
coordinada que las consultas, preservan los bytes originales, bloquean clics
duplicados y muestran errores en español. No generan nuevamente el contenido.

El flujo manual `Imagen web de pruebas` compila la interfaz en GitHub Actions,
fuera de la laptop y del servidor pequeño. Publica una imagen sin secretos,
identificada por commit y SHA-256; el despliegue admite imágenes precargadas solo
cuando su etiqueta de revisión coincide exactamente con el commit objetivo.

## Segunda mejora de navegación (18 de octubre)

- Consultas de inicio en paralelo; precarga de datos por intención al enfocar o
  acercar el puntero a enlaces. Se evita en conexiones 2G o ahorro de datos.
- Cuatro lecturas de navegación se comparten en memoria durante diez segundos.
  Las escrituras, subidas, cambios de cuenta y regreso desde caché del navegador
  invalidan los datos. No se almacenan respuestas privadas en disco, servidor
  compartido ni caché pública; el estado de sesiones en vivo no usa esta caché.
- Vistas estructurales de carga en rutas y paneles, con movimiento reducido.
  La barra de subida sigue mostrando bytes reales. No hay progreso de IA inventado.
- Validación: 269 pruebas backend aprobadas, incluidos documentos, sesiones,
  evaluación, exportación y aislamiento de propietarios; pruebas de caché cubren
  concurrencia, caducidad, mutaciones, separación de cuentas y ejecución SSR.

## Git y AWS

La entrega se integra mediante avance directo a main, preservando el historial.
El inventario `maintenance/branch-cleanup-20261018.json` conserva nombres y commits
anteriores; solo se eliminan ramas ya incluidas, después de publicar main. Los
secretos, bases locales y resultados temporales quedan excluidos de Git.
Las compilaciones de producción se ejecutan en EC2 para evitar sobrecargar la
laptop. La publicación se verifica por separado: un push no despliega por sí solo.
