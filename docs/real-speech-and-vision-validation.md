# Transcripción y detección: pruebas reales

18 de octubre de 2026. Estas comprobaciones no utilizaron la cámara del
estudiante, grabaciones personales ni transcripciones ficticias de proveedores.

## Transcripción

Se envió la muestra española sintética existente de 8,064 segundos a los
proveedores reales. Se probaron WAV y WebM/Opus, incluido el MIME con parámetros
que utiliza MediaRecorder. Los cuatro resultados contienen todas las palabras
de referencia tras normalizar tildes y puntuación. Esa cobertura no mide orden,
acentos diversos, ruido ni precisión general.

| Proveedor | Formato | Latencia observada | Resultado |
|---|---|---:|---|
| Groq | WAV | 1513 ms | Correcto |
| Gemini | WAV | 2962 ms | Correcto |
| Groq | WebM/Opus | 4274 ms | Correcto |
| Gemini | WebM/Opus | 5724 ms | Correcto |

Una primera llamada a Groq falló; las comprobaciones posteriores pasaron. No
se garantizan esas latencias ni disponibilidad permanente.

El respaldo Gemini estaba roto: requirements imponía google-genai 1.x y el
servicio rechazó explícitamente ese esquema antiguo. Se actualizó a >=2,<3
(probado con 2.31.0), generation_config, modo verbatim, audio base64 y
output_text. La llamada usa store=false y un plazo real de ejecución. Los
errores de estado de Interactions conservan su condición de reintento sin
exponer cuerpos de solicitud. pip check no encontró incompatibilidades.

Fuentes oficiales consultadas:
- https://ai.google.dev/gemini-api/docs/transcribe
- https://ai.google.dev/gemini-api/docs/interactions-breaking-changes-may-2026
- https://console.groq.com/docs/speech-to-text

Reproducir con `backend/.venv/Scripts/python.exe infrastructure/scripts/check_real_transcription.py`.
`--provider gemini` selecciona el respaldo y `--browser-audio` la muestra WebM
preparada. Cada ejecución realiza una llamada real y puede consumir cuota del
proveedor; no usa créditos AWS ni ejecuta un modelo local. No lanzar en bucle.
Los resultados quedan en `artifacts/defense-validation/real-stt-*.json`.

## Detección visual

Se cargaron los FaceLandmarker y PoseLandmarker reales del proyecto mediante
`frontend/scripts/serve-vision-check.mjs`, controlando la página por sus botones.
Se midieron seis imágenes sintéticas existentes, una por clic y sin bucle de
inferencia. No hubo peticiones a Gemini ni permiso de cámara física.

| Escenario | Presencia | Mirada | Medición |
|---|---|---|---:|
| Frente, con referencia de prueba | Presente | Centrada | 297 ms |
| Ojos izquierda | Presente | Apartada | 71 ms |
| Ojos derecha | Presente | Apartada | 73 ms |
| Ojos abajo | Presente | Apartada | 89 ms |
| Cabeza girada | Presente | Apartada | 70 ms |
| Imagen vacía | Ausente | Sin verificar | 28 ms |

Son pruebas con imágenes y el modo IMAGE de los detectores. No sustituyen una
prueba de cámara física, seguimiento VIDEO, vestimenta real o medición clínica.
La primera imagen fijó la referencia de mirada para la prueba; la aplicación
mantiene sus requisitos de calibración por muestras estables.

Datos: `artifacts/defense-validation/real-vision.json`. Evidencia:
`docs/screenshots/vision-real-models-validated.png`.

## Cambios de vestimenta

El intervalo automático ahora usa el valor configurado, en lugar de ejecutar
siempre cada diez segundos. Apagarlo se conserva por simulación y pestaña,
incluido el paso entre calibración y sala. Cuando está apagado y no hay cámara,
el estado indica apagado, no esperando captura. Se probaron las preferencias,
datos inválidos, aislamiento entre sesiones y almacenamiento bloqueado.

Validación final después de actualizar el SDK: **42 pruebas aprobadas**, cero
fallos, cero errores y cero omitidas, en 44,4 segundos. Incluye sesión con
PostgreSQL aislado, cierre, voz, transcripción y respaldo. El clúster se apagó
al terminar. Ruff, ESLint y pip check también pasaron.
