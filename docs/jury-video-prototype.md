# Jurado de video humano (prototipo académico)

Motor DH_live mini, fijado a revisión 4467e97cd97194c2c54762043cf121c6d313db12.
Recursos en frontend/public/vendor/dh-live; procedencia y condiciones en NOTICE.md.
Los personajes incluidos son ejemplos de terceros. Sustituirlos por grabaciones
autorizadas antes de presentarlos como identidades propias de Socratia.
Hay tres instancias y tres rostros diferentes: Alex y Elena son ejemplos del
repositorio; Daniel es un personaje ficticio creado para Socratia y preparado
localmente con los modelos oficiales. Véase jury-avatar-generation.md.
Su boca se anima con el audio. Los clips de escucha añaden movimiento facial
generado previamente con FasterLivePortrait; no generan gestos corporales nuevos.
Los ejemplos estilizados no se seleccionan.

Cada personaje reproduce un clip silencioso de escucha con parpadeos y giros
de cabeza reales en los fotogramas. El reproductor limita el dibujo a 15 fps;
los tres tienen fases distintas. El desplazamiento CSS del retrato ya no se carga.
Respeta movimiento reducido, visibilidad y pausa global. Solo el jurado que
recibe audio activa el motor labial; los demás siguen escuchando. Al terminar,
interrumpir o cambiar de jurado vuelve a su clip de escucha. Reanudar animaciones
reanuda los tres personajes. Si el clip falla, se conserva el encuadre neutral.
Son bucles preparados previamente, no reacciones generadas para cada respuesta.
Preparación, modelos y límites: jury-facial-motion.md.

La prueba permite comparar Kokoro (em_alex, ef_dora, em_santa), Piper sharvard
y las voces anteriores de Windows. Kokoro proporciona tres voces diferentes.
Los ejemplos de comparación usan la misma pregunta para comparar timbre y demora.
El respaldo del navegador prioriza voces españolas masculinas/femeninas por
nombre disponible; el resultado depende del catálogo del sistema.

El backend local usa Kokoro CPU mediante compose.local-voice.yaml. Los modelos
se descargan explícitamente con infrastructure/scripts/benchmark_jury_voices.py,
nunca durante una petición. Modelo INT8 de 92,4 MB, voces 28,2 MB. Configuración:
VOICE_TTS_ENABLED=true, LOCAL_TTS_ENABLED=true, LOCAL_TTS_MODEL_DIR=/data/voice-models.
El overlay necesita SOCRATIA_VOICE_MODELS apuntando al directorio de modelos.
AWS conserva su configuración previa; este overlay todavía no está desplegado.

Para reconstruir: primero construir la imagen base `socratia-backend` con el
Dockerfile del backend; luego construir `socratia-backend-local-voice` con
infrastructure/staging/Dockerfile.local-voice desde la raíz. Levantar el backend
con `docker compose -f compose.yaml -f compose.local-voice.yaml up -d --no-deps --no-build backend`.
Los modelos de uso local están en C:/Users/ElCremosasWee/.codex/models/socratia-voice,
fuera de Temp; SOCRATIA_VOICE_MODELS está fijado en el .env local. No se incluyen
los pesos en Git ni en el paquete de código para AWS.

Medición en este PC (misma pregunta, unos 8 s de audio): Kokoro INT8 3,8–4,4 s
tras la primera carga; Piper 0,3 s en la segunda ejecución. Primera carga de
Kokoro en el contenedor: 9,0 s para una frase más corta; repetición desde caché
menor a 1 ms en esa comprobación. No son mediciones de AWS ni garantías de calidad.
Resultados y checksums: frontend/public/vendor/dh-live/common/neural/benchmark.json.

El endpoint autenticado /simulations/{id}/speech comprueba propiedad y solo lee
la pregunta activa (con un saludo permitido), no texto arbitrario. Devuelve WAV
y no permite cacheado HTTP. Caché interna volátil: hasta 16 entradas / 8 MB;
una inferencia CPU a la vez, dos hilos ONNX. Si está ocupado o falla, se usa el
respaldo del navegador. La primera carga es más lenta; no se promete latencia
idéntica en t3.small.

Al comenzar la respuesta oral, /speech/prewarm prepara solo la siguiente pregunta
existente del banco (máximo 800 caracteres), sin llamar a LLM ni enviarla al cliente.
Una repregunta puede sustituirla; ese audio anticipado puede no utilizarse.
Interrumpir y tomar la palabra cancela reproducción/petición y abre la grabación
cuando la sesión admite respuesta. La interrupción es mediante botón, no VAD
continuo sobre el audio del jurado. El trabajo CPU ya iniciado termina en segundo
plano, con concurrencia limitada.

La sala permite seleccionar Video humano (experimental) o personajes 3D.
Cada jurado tiene un iframe independiente y solo acepta mensajes del mismo
origen y de su padre. No envía cámara, micrófono ni audio a DH_live/MatesX.
La voz permanece en el reproductor de Socratia; el iframe solo recibe WAV mono
PCM16 16 kHz para animar la boca. El cuerpo sigue el video base.

El audio del servidor se decodifica y se convierte a WAV para el motor. Si tarda
en prepararse, se recorta al momento de reproducción actual. La voz sintetizada
por el navegador no expone PCM: durante esa intervención se utiliza el jurado
3D, evitando mostrar un video silencioso como si sincronizara la voz. Habilitar
TTS del servidor para usar sincronización labial de video en toda la sesión.
El modo video vuelve automáticamente después de la intervención.

Si falla el motor o tarda más de 30 s, se vuelve al personaje 3D. Pausar
animaciones detiene el video y su bucle de procesamiento. Desmontar el iframe
libera el entorno WebAssembly. No se crean nuevos servicios de AWS.

Prueba independiente: http://localhost:3000/vendor/dh-live/lab.html
Incluye muestras españolas de Kokoro, Piper y Windows, generadas localmente.
Permite comprobar tres cargas simultáneas, voz por turnos y pausa sin consumir
Gemini/Groq. No demuestra aún rendimiento con cámara ni calidad en una defensa
completa. La prueba usa personajes de ejemplo y conserva la marca MatesX.

## Carga del jurado y cambio involuntario a 3D

Se encontró que `VideoJuryCharacter` cambiaba a un personaje 3D al hablar con
SpeechSynthesis, porque esa API no entrega PCM al sincronizador. El inicio además
levantaba tres motores WASM incluso cuando la voz no podía utilizarlos.

La corrección mantiene un reproductor humano ligero con los clips de escucha
existentes. Solo pide el motor de labios cuando el jurado activo tiene un
AudioBuffer real. Ante fallo del motor conserva el humano; el modo 3D queda como
selección explícita. La voz del navegador no tiene sincronización labial exacta:
el clip sigue mostrando movimiento de escucha, no una boca inventada.

El reproductor ligero limita el dibujo a 10 fps y 288×384; se detiene al ocultar la
pestaña, al pausar o con movimiento reducido. Conserva los archivos y marcas de
origen. Pruebas locales aprobadas: adaptador de turnos, movimiento de escucha,
reproductor ligero (croma, origen, pausa, visibilidad y movimiento reducido),
ESLint del componente. La latencia y calidad visual requieren verificación en AWS.

Publicación confirmada: frontend reconstruido en EC2 y contenedor recreado.
Imagen anterior conservada como `socratia-staging-frontend:jury-before-20261018`;
fuentes previas en `/opt/socratia/jury-backup-1792372147`. Se comprobaron en HTTPS
los reproductores humanos de los tres índices; Alex y Elena muestran sus clips
correctos sin importar WASM. El navegador de validación tiene movimiento reducido
activado: se confirmó la presentación de un fotograma humano y vídeo pausado,
como corresponde a esa preferencia. No se midió todavía el tiempo de una defensa
completa con caché fría ni sincronización labial con audio real en AWS.
Captura: `docs/screenshots/staging-human-alex.png`.
