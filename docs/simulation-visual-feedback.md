# Simulación: personajes y cámara

## Comportamiento

- El tribunal usa tres modelos GLB humanos articulados, renderizados con Three.js y TalkingHead 1.7. Parpadean, miran al interlocutor y realizan gestos de manos y cabeza. No usa los retratos estáticos como jurados.
- El personaje que tiene el turno mueve la boca durante la reproducción. Con audio TTS, la apertura responde al análisis del audio y se reduce durante el silencio. Las formas de vocales son aproximadas; no es alineación fonética profesional. Con síntesis del navegador, que no expone PCM, usa los eventos de palabra y el inicio/fin de la voz para una articulación estimada.
- Pausar animaciones detiene el movimiento del tribunal; la voz puede continuar. Sin WebGL, se muestra una explicación y se conserva el flujo por voz/texto.
- La cámara previamente calibrada se activa al entrar en una sesión activa. Se puede apagar desde “Tu espacio”. Los modelos y WASM de MediaPipe se sirven localmente para evitar depender del CDN durante la sesión.
- Presencia se reconoce mediante rostro **o** puntos del cuerpo. Tres fotogramas consecutivos sin detección cambian el indicador a ausencia. Una falla de inferencia o video pausado es “sin medición”, no presencia ni ausencia certificada.
- Ojos y orientación facial usan FaceLandmarker. Hombros, manos y torso usan PoseLandmarker. Si no se ve la cadera, no se publica un ángulo del torso. No se inventan puntuaciones de postura ni se clasifica sentado/de pie sin datos.
- Vestimenta se revisa automáticamente al detectar presencia, con una nueva captura cada 10 segundos y un control visible para desactivarla. La interfaz informa que la captura JPEG se envía a Gemini. También permite una revisión manual. El endpoint exige autenticación y propiedad de la simulación. La captura no se escribe en archivos, base de datos, reportes ni transcripciones. Presencia/mirada/postura permanecen locales.
- La revisión de ropa distingue saco, camisa con cuello y corbata; no considera obligatoria la corbata. Con encuadre insuficiente, baja confianza o ausencia, devuelve una conclusión incierta. La interfaz muestra cuándo se hizo la última revisión y borra el resultado al perder presencia/apagar la cámara.

## Configuración

`GEMINI_API_KEY` habilita vestimenta. `VISION_MODEL` permite cambiar el modelo; el valor inicial `gemini-3.1-flash-lite` se comprobó con la cuenta de desarrollo. Si el proveedor falla, se presenta el error y no se genera una valoración ficticia. La revisión continua está activa por defecto durante la comprobación y la práctica; puede desactivarse y realiza solicitudes al proveedor.

## Dependencias y modelos

- [TalkingHead](https://github.com/met4citizen/TalkingHead), MIT, Mika Suominen. Copia local de la versión 1.7 en `frontend/src/vendor`, con licencia en sus cabeceras. Se deshabilitó exclusivamente el import dinámico de procesadores de idiomas no utilizados, incompatible con Turbopack; Socratia conserva la reproducción de voz y controla los morphs desde su adaptador.
- Three.js 0.180, MIT, instalado por npm.
- MediaPipe Tasks Vision 1.0.1, Apache-2.0; WASM copiado del paquete instalado y modelos Pose/Face de los recursos oficiales de Google.
- `academic-base.glb`: ejemplo MPFB de TalkingHead, CC0; modelo femenino de MakeHuman/MPFB.
- `alex.glb`: ejemplo AvatarSDK de TalkingHead. `daniel.glb`: ejemplo Avaturn de TalkingHead (en la interfaz corresponde a Elena). Estos dos son **modelos de demostración para las pruebas locales no comerciales** según la atribución del proyecto original. Antes de distribuir comercialmente el producto deben sustituirse por personajes propios o modelos con licencia adecuada. La licencia MIT de TalkingHead no licencia automáticamente sus avatares. [Atribuciones originales](https://github.com/met4citizen/TalkingHead#the-indexhtml-test-app).

## Validación reproducible

```powershell
cd frontend
npm run test:signals
node scripts/test-live-vision.mjs
```

El segundo script requiere la aplicación local y Edge. Intercepta únicamente los datos y WebSocket de una sesión ficticia; no modifica cuentas, sesiones ni reportes. Ejecuta los detectores reales sobre video de una persona, un fondo vacío y la persona de nuevo, carga los tres rigs y reproduce audio de prueba con un intervalo silencioso. Verifica que la boca se activa, se cierra durante silencio y se detiene al terminar. Guarda capturas en `%TEMP%/socratia-vision-validation`.

Pruebas del servicio: `python -m pytest tests/test_appearance.py tests/test_voice_pipeline.py` desde `backend` con sus dependencias. Se verificaron también solicitudes reales: saco y camisa → formal; encuadre vacío → ausencia/vestimenta incierta. Esto no reemplaza una comprobación con diferentes cámaras, iluminación, ropa y personas reales.

## Corrección v3: mirada y avisos observables

La clasificación de mirada anterior usaba solo expresiones y posición de la nariz, y por descarte daba contacto visual. Ahora mide ambos iris respecto a las esquinas y párpados, separa orientación de cabeza y mirada ocular, y no aprueba sin iris verificables. Se puede guardar una referencia mirando a la lente durante dos segundos. Se muestran posición relativa de iris, puntos superpuestos en la cámara y fotogramas analizados. Si la cámara se congela, se invalidan las señales en vez de conservar indicadores verdes.

Preparación y sala comparten el bloque “Tu presentación en vivo” (antes “Análisis en vivo · v3”). Sus estados cambian entre mirada centrada/apartada/sin verificar, presencia/ausencia, postura y ropa. Se muestran juntos los problemas de mirada y ropa. En la sala hay avisos de voz, con deduplicación y sin interrumpir grabación o reproducción; se pueden apagar. La ropa puede ser formal, casual, incompleta (torso claramente sin prenda) o incierta. El torso recortado no equivale a falta de ropa.

`npm run test:gaze` renderiza un rig humano con ojos desplazados a izquierda, derecha y abajo manteniendo la cabeza fija, y con cabeza girada. Ejecuta FaceLandmarker real sobre esos fotogramas; no sustituye sus resultados. Guarda evidencia en `%TEMP%/socratia-gaze-validation`. `npm run test:appearance:provider` es una prueba opcional contra el proveedor real, con imágenes de prueba generadas/renderizadas; requiere las variables `SOCRATIA_APPEARANCE_TEST_EMAIL` y `SOCRATIA_APPEARANCE_TEST_PASSWORD` de una cuenta local con una simulación existente. No usa la cámara física ni modifica la simulación. Estas pruebas controladas no certifican precisión para todas las cámaras o condiciones de iluminación.


`node scripts/test-camera-provider-live.mjs` prueba el flujo completo de la pantalla con FaceLandmarker/PoseLandmarker y el endpoint real de vestimenta. Usa la cuenta local suministrada por las variables anteriores; intercepta solamente las lecturas de sesión y su WebSocket para no modificarla. Cambia el video de prueba entre ropa formal, camiseta, torso sin prenda y un recorte de cara/hombros. Verifica los avisos visibles de mirada y ropa y la invalidación al desaparecer la persona. La evidencia queda en `%TEMP%/socratia-camera-provider-validation`.

La captura incluye evidencia local `torso_in_frame`, calculada con hombros y espacio visible por debajo de ellos. Si falta ese encuadre, el servidor invalida una conclusión de ropa formal/casual: devuelve incierto y solicita mostrar el torso, aunque el proveedor haya intentado clasificarlo. Los datos no se guardan como una calificación ni se utilizan para negar el acceso a la práctica.


## Revisión integral del 15 de octubre de 2026

- Exposición local a partir de luminancia en un canvas de 96 × 72: oscuridad, sobreexposición y contraluz cuando hay rostro medible. No clasifica tonos de piel ni almacena capturas. Es una ayuda de encuadre, no un certificado de calidad de imagen.
- FaceLandmarker admite dos rostros. Si detecta más de uno, se invalidan mirada/postura individuales y se pausa vestimenta para no mezclar personas. Esto cuenta rostros detectados; no garantiza detectar personas tapadas o fuera del encuadre.
- Avisos sostenidos: mirada/encuadre 1,5 s, ojos cerrados y postura 2,2 s, manos cerca de la cara 2,5 s. Un parpadeo o un fotograma aislado no genera corrección de voz. Se lee un aviso cada vez, con separación mínima de 20 s y 60 s antes de repetir la misma condición.
- Se invalidan muestras de calibración al faltar imágenes nuevas. Hay reinicio de cámara, actualización de dispositivos al conectarlos/desconectarlos y mensajes específicos de permisos/dispositivos ocupados. La preparación exige rostro y hombros verificables, un solo rostro, exposición utilizable y señal de micrófono.
- El jurado saluda y lee automáticamente la primera pregunta. Las preguntas posteriores por texto también se leen. El TTS del servidor tiene prioridad para evitar voces duplicadas; el bloqueo de reproducción del navegador se explica y se reintenta tras una interacción.
- Conversación automática en modo voz cuando el micrófono fue preparado: abre el micrófono al terminar el jurado y envía tras cuatro segundos sin actividad sonora, después de al menos 600 ms de actividad. Es detección de sonido, no reconocimiento semántico de voz. Tras 20 s sin actividad suficiente se pausa y descarta la grabación; no avanza la pregunta. El control permite pasar a envío manual y se conserva el límite de dos minutos.
- El servidor permite cancelar la intervención de voz activa por su identificador, libera el buffer y procesa desconexiones y mensajes JSON mal formados sin dejar el bucle bloqueado.
- Vestimenta invalida el resultado previo ante error, limita la espera del navegador a 30 s y diferencia demora del proveedor. Los logs contienen solo categoría de fallo y estado HTTP, nunca imágenes, cuerpos del proveedor ni claves.

Validación adicional: `npm run test:coach`, `npm run test:dialogue`, `npm run test:turns`, `npm run test:gaze:camera`. La prueba de cámara cubre oscuridad, sobreexposición, dos rostros, timestamp de decodificador congelado, recuperación/reinicio y fallo del proveedor seguido de recuperación. El congelamiento usa un timestamp controlado; una imagen estática con timestamp que avanza no se puede distinguir con certeza de una persona quieta.

Se verificó el flujo real contra Gemini: formal → camiseta/casual → torso sin prenda/incompleto → recorte/incierto → ausencia. Hubo un fallo transitorio del proveedor durante la revisión; una ejecución posterior completó los cuatro casos con HTTP 200. La disponibilidad de Gemini sigue siendo externa. Estas pruebas usan escenas y audio controlados, no la cámara física del usuario.
