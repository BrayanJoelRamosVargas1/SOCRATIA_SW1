# Generación local de movimientos del jurado

Actualización posterior del 18 de octubre: la versión sintética de Alex se
revirtió porque degradaba sus párpados. `assets/01.mp4` y los datos faciales
vuelven al paquete original; `assets/listening.mp4` usa ese mismo video para
mantener expresiones naturales y continuidad. Elena y Daniel conservan los
clips generados. No reimportar el paquete de tres avatares anterior sin revisar
la expresión de Alex. El respaldo está en `artifacts/jury-remote/expression-voice-backup`.

Las muestras Kokoro y el proveedor opcional tienen perfiles de tono/ritmo:
Alex 1.06/.98, Elena 1.10/1.05 y Daniel .88/.90. Son ajustes de las voces
em_alex, ef_dora y em_santa, no nuevas identidades vocales. El proveedor usa
resample_poly con compensación de velocidad y requiere scipy. El script
`refine_jury_samples.py` reproduce los cambios de muestras sin inferencia.

Motor: [FasterLivePortrait](https://github.com/warmshao/FasterLivePortrait),
revisión `8aad3602177547aaa5e4beec0c3ef5b7944e7a1f`.
Pesos ONNX públicos de `warmshao/FasterLivePortrait` en Hugging Face,
revisión `eb937f4bec7186598df2d1f68e1ddbb488ae1de5`.
El código del motor es MIT; los modelos conservan sus condiciones respectivas.
Esta integración se prepara para el prototipo académico, sin contratar APIs.

Se parte del encuadre neutral del video de cada personaje. El modelo modifica
la geometría facial: pequeñas rotaciones de cabeza y cierre de párpados.
Los objetivos se generan por código; no se sube la cámara del estudiante ni
se transfiere la actuación de otra persona. No genera gestos nuevos de manos
ni movimiento corporal completo. Los clips son bucles, no reacciones generativas
a cada respuesta del estudiante.

## Reproducir la preparación

**Ruta recomendada: GPU remota.** Ejecutar el empaquetador ligero
`python infrastructure/scripts/package_remote_jury.py` para obtener el notebook
y el ZIP de entrada en `artifacts/jury-remote`. Abrir Google Colab, subir el
notebook y seleccionar una GPU gratuita. Nunca conectar un entorno local.
El notebook comprueba GPU y CUDA, procesa los tres personajes en orden y devuelve
un ZIP con los videos y sus hashes. No monta Drive ni incluye credenciales.
La disponibilidad y las cuotas gratuitas dependen de Colab. Validado el
2026-10-18 en una Tesla T4 de Colab: los tres clips se generaron remotamente,
decodificaron sus 120 fotogramas a 15 fps y se importaron verificando SHA-256.
Tamaños: Alex 145902 bytes, Elena 146994 bytes, Daniel 197693 bytes.
Notebook ejecutado: https://colab.research.google.com/drive/1jtQK92pgjCKMR-lH6zHaYI_sTNjH6btK
La ruta CUDA usa búsqueda cuDNN DEFAULT con TF32 desactivado para compatibilidad
con T4. El pegado final mantiene sus tensores en CPU del servidor remoto para
evitar mezclar dispositivos con torchgeometry. Los avisos de fallback de
convolución no impidieron completar la generación; duró unos cinco minutos.

El render en Windows está bloqueado por defecto para proteger la laptop.
Solo se puede habilitar deliberadamente con `--allow-local-render`; no es la
ruta recomendada para este equipo. Los archivos terminados se reproducen localmente.

Usar un entorno Python independiente con
`infrastructure/requirements-portrait-motion.txt`. Clonar el motor fuera del
repositorio de Socratia y fijar la revisión anterior. Descargar explícitamente:

```powershell
python infrastructure/scripts/download_portrait_motion.py ENGINE_ROOT/checkpoints/liveportrait_onnx
python infrastructure/scripts/render_jury_listening.py --engine-root ENGINE_ROOT --source NEUTRAL_FRAME.png --output listening.mp4 --phase 2.7 --frames 60 --fps 15
```

El script adapta únicamente ese checkout externo para CPU: elimina la
inicialización CUDA incondicional, usa el proveedor CPU y sustituye la clase
contenedora `Face` por un diccionario equivalente. No instala InsightFace.
Convierte los dos operadores personalizados `GridSample3D` del export TensorRT
al operador ONNX estándar `GridSample` de opset 20 con el convertidor oficial.
Conserva los pesos originales y verifica el grafo convertido antes de guardarlo.
La salida final se codifica H.264/YUV420p con metadatos al inicio para navegador.

La opción `--directml-runtime PATH` permite probar una instalación separada de
`onnxruntime-directml` en Windows. No sustituye el entorno de voz ni añade una
dependencia al servidor. Los operadores no compatibles pueden recaer en CPU;
no se garantiza aceleración por disponer de una GPU.

Para preparar también sincronización labial a partir de un clip animado:

```powershell
python infrastructure/scripts/prepare_jury_avatar.py --video --source listening.mp4 --engine-root DH_LIVE_ROOT --output OUTPUT_FOLDER
```

## Reproducción

`listening-motion.js` reproduce un video local silenciado e independiente por
jurado. Al recibir voz, `bridge.js` detiene ese reproductor y activa el motor
labial. Al terminar o interrumpir el turno, vuelve a la escucha. La pausa global,
la visibilidad y la preferencia de movimiento reducido detienen el bucle.
Si falta un clip, se conserva el encuadre neutral. El desplazamiento CSS del
retrato completo ya no se carga desde `player.html`.

Los pesos grandes son herramientas de creación; AWS recibe únicamente los
clips terminados y los recursos existentes de DH_live. Esta animación no llama
a Gemini, Groq ni servicios de avatares. El alojamiento y la transferencia de
los archivos siguen sujetos al consumo normal del servidor.

Pruebas del reproductor: `npm run test:video-jury` desde `frontend`.
Prueba visual: `http://localhost:3000/vendor/dh-live/lab.html`.

## Preparación remota del habla

`infrastructure/scripts/prepare_remote_speaking.py` prepara las tres bases
de DH_live en Colab, usando los clips animados de escucha como entrada.
Requiere GPU remota y rechaza Windows. Instalar allí las dependencias de
`infrastructure/requirements-speaking-assets.txt`; no ejecutar el render en
la laptop. Los archivos de entrada no incluyen cámara, cuentas ni claves.

La preparación conserva los 8 segundos y desactiva la duplicación inversa del
motor para mantener la misma fase entre escuchar y hablar. Usa la revisión
de DH_live indicada en `frontend/public/vendor/dh-live/NOTICE.md`, con sus
tres checkpoints públicos de DINet_mini, SCRFD y FaceLandmarker.

El paquete final contiene los videos de escucha, los videos de habla a 25 FPS
y sus datos faciales. El importador `import_remote_speaking.py` verifica la
lista de archivos, tamaño, SHA-256 y correspondencia entre fotogramas y datos;
guarda las versiones anteriores en `artifacts/jury-remote/previous-speaking`.

El reproductor transfiere el tiempo del video al cambiar de escucha a habla y
al regresar. Los fragmentos siguientes de audio no reinician el movimiento.
Esto añade giros de cabeza y parpadeos durante las preguntas; no genera
gestos de brazos ni movimientos nuevos del cuerpo.

Validado e importado el 18 de octubre de 2026: Alex, Elena y Daniel tienen
200 fotogramas de habla a 25 FPS y 200 entradas faciales cada uno. El ZIP
de resultados ocupa 1.548.217 bytes. La preparación remota decodificó todos
los fotogramas y el importador local comprobó los hashes antes de reemplazar
los recursos. ESLint de los dos adaptadores y las pruebas del reproductor pasan.

### Prueba del reproductor completo

Se verificaron en navegador los turnos de Alex, Elena y Daniel con las voces
Kokoro, la interrupción al elegir otro jurado, la pausa y la reanudación.
Las voces de muestra son PCM a 24 kHz: `lip-audio.js` las decodifica a 16 kHz
y genera WAV mono PCM16 para el motor labial, sin cambiar la voz audible.
La sala React ya realiza esa conversión en `video-jury-character.tsx`.

El temporizador del motor conserva el tiempo restante durante una pausa.
En el laboratorio también se pausa el audio audible. Las pruebas ligeras
cubren esa duración y el formato de entrada. Los adaptadores usan una revisión
en su URL para evitar reutilizar archivos anteriores de la caché.

Esta comprobación corresponde al laboratorio de reproducción, sin backend,
micrófono ni solicitudes de preguntas a los proveedores. No constituye una
validación completa de una defensa con respuestas del estudiante.
