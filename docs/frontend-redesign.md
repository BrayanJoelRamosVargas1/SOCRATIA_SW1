# Revisión de experiencia y simulación — Socratia

## Cambios implementados

- Portada pública: restaurada la versión original por preferencia del usuario, conservando su contenido, composición y paleta. Las mejoras se concentran en menús y pantallas internas.
- Lenguaje visual común: tipografía, colores, botones, tarjetas, formularios, estados, accesibilidad de teclado y tamaños de pantalla.
- Administrador: KPIs acumulados, distribución por estado, errores, procesos pendientes, conversión de simulaciones y documentos, promedio de evaluaciones. Cada métrica se deriva de `/admin/dashboard`; no se inventan cambios porcentuales ni disponibilidad de proveedores.
- Tribunal: tres personajes SVG originales con respiración, parpadeo, gestos y movimientos durante la reproducción de voz. Se puede pausar la animación y se respeta movimiento reducido. La boca usa una animación ilustrativa, no sincronización fonética ni captura facial.
- Sala: pregunta, avance, estado de turno, respuesta oral/escrita, conversación desplegable y panel de cámara. Conexión WebSocket estable durante los cambios de pregunta; reenvío idempotente de respuestas escritas pendientes; limpieza de micrófono, cámara, contexto de audio y URLs temporales.
- Voz: envío manual y límite de dos minutos; una pausa breve ya no envía prematuramente el audio. Conteo descriptivo de palabras, repeticiones y posibles muletillas sobre la última transcripción recibida, sin diagnosticar tartamudez ni puntuar silencio.
- Cámara: puntos con visibilidad suficiente, encuadre, inclinación de hombros, manos visibles y referencia obtenida de varias muestras. Sin puntos confiables, no hay medición. Runtime de MediaPipe fijado a la versión instalada.
- Preparación: prueba explícita de cámara/micrófono; se elimina la supuesta certificación de presencia basada en movimiento de píxeles. La API actual exige los tres indicadores de dispositivos para pasar a READY.
- Reporte: solo puntuaciones y disponibilidad del servidor. Se eliminan notas de relleno de localStorage, vestimenta y conclusiones de aprobación universitaria. Consulta con espera acotada, recuperación de errores y expansión de respuestas al imprimir.

## Elementos retirados

- Clasificación de ropa mediante colores o píxeles y penalizaciones por prendas.
- Inferir manos en bolsillos por proximidad de muñecas a caderas.
- Presentar geometría de cabeza como contacto visual exacto.
- Controles de demostración que fingían ausencia, vestimenta y puntuaciones en la sesión real.
- Porcentajes iniciales de postura y fluidez sin muestras.
- Proveedores supuestamente conectados cuando el backend devuelve NOT_AVAILABLE.
- Etiquetas CU, RAG, chunks y nombres de infraestructura en recorridos del estudiante, donde se identificaron.

## Próximos incrementos recomendados

1. Analítica temporal en backend: usuarios activos diarios/mensuales, retención, finalización por semana y comparación entre periodos. El panel actual muestra acumulados, no tendencias.
2. Monitorización por proveedor: disponibilidad verificada, latencia p50/p95, errores, uso de fallback y costos medidos. El endpoint actual no publica esos datos.
3. Modo de preparación solo texto, sin requisitos de cámara/micrófono. Requiere modificar explícitamente el contrato y las reglas de DRAFT/READY del backend; no se falsean indicadores para saltarlos.
4. Medición visual validada y voluntaria: calidad de imagen, cobertura de muestras, pruebas en iluminación/dispositivos diversos y evaluación de falsos positivos antes de incorporarla a una rúbrica.
5. Comparación entre prácticas del mismo documento y objetivos de mejora persistidos; tendencias paginadas calculadas en servidor.
6. Ampliar pruebas de servicios reales y dispositivos físicos. Ya se recorrió el flujo autenticado con PostgreSQL aislado y proveedores controlados; falta certificar pgvector y voz externos, cámara y micrófono reales.
7. Auditoría de cambios administrativos (quién, cuándo, antes/después), filtros por fecha y estados, y paginación en los listados que aún cargan colecciones completas.

## Verificación

- Compilación completa Next.js, TypeScript y empaquetado standalone aprobados usando `SOCRATIA_WORKER_THREADS=1` (opción documentada para entornos sin procesos hijos).
- ESLint y comprobación de TypeScript aprobados.
- Pruebas de renovación de sesión concurrente, errores de permisos, respuestas vacías y recuperación tras fallos: aprobadas.
- Quince comprobaciones de señales visuales/transcripciones: aprobadas.
- 228 pruebas del backend aprobadas (7 min 7 s), incluidas regresiones de zona horaria, permisos, reconexión, documentos, reportes y suscripciones concurrentes. Se excluyó la prueba que exige credenciales de voz externas.
- Veintiuna rutas devolvieron HTML con HTTP 200 en el servidor de producción. Esta comprobación no equivale a un flujo autenticado ni a una revisión visual.
- Revisión visual realizada en navegador de escritorio y a 390 × 844: portada, tribunal, panel administrativo, documentos, configuración, calibración, sala, reporte e historial.
- Flujo de administrador: login, consulta de usuarios/jurados/IA, creación de plan de prueba, asignación de plan gratuito, búsqueda de usuarios por nombre/correo y logout.
- Flujo de estudiante: login, carga de DOCX, procesamiento, 12 preguntas, estructura de exposición, nueva simulación, respuesta escrita, avance a pregunta 2, recarga conservando la pregunta, cierre manual, reporte e historial; edición de biografía y logout.
- Se comprobó que un estudiante recibe rechazo del backend en administración y ve una pantalla de acceso restringido, sin consola ni datos administrativos.
- Se corrigió un fallo real: reemplazar tzinfo en lugar de convertir la zona horaria cerraba sesiones bolivianas después de la primera respuesta. Las tres comprobaciones de duración usan ahora el normalizador UTC existente.
- Se corrigió una regla CSS global que ocultaba los botones secundarios en móvil, incluido cancelar el cierre de sesión. Botones, Escape y retorno de foco comprobados.
- El backend reconoce más estados documentales que el frontend anterior: se incorporaron las etiquetas de cola, extracción, fragmentación, embeddings, reintentos, cambio de proveedor, indexación y degradación.
- Entorno aislado: PostgreSQL 15 temporal, cuentas y documento sintéticos. La instalación nativa no contiene pgvector: se usó un dominio de prueba de serialización y FakeVectorStoreProvider. No certifica búsquedas vectoriales reales.
- Cámara/micrófono físicos no se activaron. La transición de calibración se probó mediante señales sintéticas en el entorno aislado; la UI bloquea guardar si no hay señales.
- Los resultados de evaluación y preguntas del recorrido visual provinieron de dobles deterministas, no de llamadas de IA reales. Las notas mostradas en las capturas son datos de prueba.

Para desarrollo normal: `npm run dev`. En un entorno que restrinja procesos hijos, establecer `SOCRATIA_WORKER_THREADS=1` y usar las opciones del framework. Esta variable conserva las comprobaciones de tipos; no utiliza ignoreBuildErrors.


## Capturas de validación

- `docs/screenshots/validation/admin-final.png`: panel con actividad real del entorno de prueba (2 usuarios, 1 documento y 2 simulaciones evaluadas).
- `backend/scripts/validation_server.py`: servidor de validación expresamente limitado a una base `socratia_ui_test`. Nunca debe usarse como servidor de producción: reemplaza los proveedores con dobles.
