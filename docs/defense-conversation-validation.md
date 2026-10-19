# Conversación de defensa: estado de validación

## Actualización: integración con PostgreSQL aislado

Se habilitó un lanzador reproducible en
`infrastructure/scripts/run_defense_tests.py`. Utiliza PostgreSQL nativo en un
puerto local libre, una base nueva llamada `socratia_defense_test`, credenciales
aleatorias y 32 MB de buffers compartidos. No modifica el servicio de PostgreSQL
del equipo ni la base de Socratia. Apaga su propio clúster al terminar y conserva
el resultado en `artifacts/defense-validation/defense-tests.xml`.

La primera ejecución completó las 17 pruebas de sesión, cierre, voz local y
cancelación: cero fallos y cero omitidas. La segunda completó 20 pruebas,
incluyendo nuevas comprobaciones del recorrido oral. Esto sustituye la limitación
de PostgreSQL ausente registrada más abajo.

Correcciones del recorrido oral:

- Verifica propiedad de la sesión antes de consultar transcripciones o llamar
  proveedores. Un mismo identificador oral ya procesado recupera su resultado
  sin repetir transcripción, decisión del jurado ni avance de pregunta.
- Guarda la transcripción junto con la aceptación de la respuesta. El silencio
  no deja una respuesta ni una transcripción completada en la base.
- Si la respuesta cierra la sesión por tiempo, no solicita una nueva decisión
  ni voz para otra pregunta.
- Si falla la configuración del jurado, continúa con la siguiente pregunta
  del banco; si falla la voz, conserva la pregunta para lectura en navegador.

Los proveedores se sustituyen por dobles deterministas: estas pruebas validan
persistencia, turnos, acceso y recuperación, pero no calidad de transcripción,
latencia real de Gemini/Groq ni permisos del micrófono del navegador.

Resultado final: **22 pruebas, cero fallos, cero errores y cero omitidas**,
en 33,2 segundos. Incluye los fallos de configuración del jurado y de voz.
El clúster temporal quedó apagado; Ruff también pasó en los archivos cambiados.

## Recorrido validado en pantalla

Se ejecutó la aplicación actual mediante Next dev/webpack con un límite de
768 MB de heap, compilando solo las páginas visitadas. El servidor compilado
anterior era del 15 de octubre y carecía de enlaces a sus archivos estáticos:
se añadieron junctions locales para comprobar el acceso, pero se cambió al
código actual antes de validar la sala.

Recorrido comprobado con la cuenta ficticia `validation.student@example.com`:
acceso, carga de DOCX ficticio, procesamiento de nueve fragmentos, generación
de doce preguntas de prueba, saludo automático, dos respuestas por texto,
avance hasta la tercera pregunta, recarga conservando las dos respuestas,
cierre y reporte de las dos respuestas. La nota 82 es un resultado fijo del
evaluador de pruebas, no una evaluación de IA real. Comunicación y lenguaje
corporal quedaron sin nota por ausencia de evidencia.

La calibración de la sesión controlada se preparó como fixture. El navegador
denegó acceso a la cámara; no se validaron presencia, ojos o ropa reales. Se
descartó la toma de micrófono al cerrar, sin enviarla para transcripción.

La recarga exponía un fallo: restablecía voz automática y cámara a pesar de
las elecciones del usuario. Se añadieron preferencias por sesión en
sessionStorage, sin audio, imágenes ni transcripciones. Se verificó en pantalla
que sobreviven el modo texto y la apertura manual del micrófono. La prueba
unitaria adicional cubre aislamiento entre defensas, tipos inválidos y
almacenamiento bloqueado. La preferencia de cámara se restaura desde la misma
configuración. ESLint pasó en los dos archivos cambiados.

El piloto de UI se ejecuta con `python infrastructure/scripts/run_defense_tests.py --ui`.
Los proveedores externos son dobles deterministas; el servidor de validación
también sustituye STT, decisión del jurado y TTS, para que una toma accidental
no llame servicios externos. En ese entorno el STT devuelve un texto fijo
claramente identificado, sin transcribir el audio recibido.

Al terminar se apagaron el servidor de interfaz, el servidor de validación y
su clúster PostgreSQL. La base habitual del equipo quedó intacta. La evidencia
de pantalla está en `docs/screenshots/defense-ui-report-validated.png`.

18 de octubre de 2026. El flujo existente anuncia la pregunta, intenta voz del
servidor y recurre a voz del navegador. En conversación automática abre el
micrófono después del turno del jurado y envía tras cuatro segundos de silencio
posteriores a sonido sostenido. El estudiante puede cambiar a texto o desactivar
el modo automático.

Cambios de esta revisión:

- Un error del elemento de audio HTTP intenta la voz del navegador antes de
  ceder el turno. La finalización normal conserva el comportamiento anterior.
- La medición de volumen y silencio usa un intervalo de 80 ms en lugar del
  refresco visual, reduciendo actualizaciones y evitando depender de fotogramas.
- Se solicita activar explícitamente el contexto de audio del micrófono. Si
  falla se cancela la toma, se desactiva la apertura automática y se ofrece texto.
- El límite de dos minutos descarta una toma sin sonido sostenido. El servidor
  sigue siendo responsable de transcribir y decidir si la respuesta es válida.

Verificado sin inferencia, compilaciones grandes ni servicios de pago:
ESLint de los componentes cambiados, test-visual-coach.mjs (incluye muestreo
a 80 ms y rechazo de un clic), test-practice-signals.mjs y
test-video-jury-turns.mjs. Pytest de voz local y cancelación completó seis
pruebas. Las siete pruebas de test_simulation_sessions.py se omitieron por
no estar disponible PostgreSQL de pruebas en el puerto 5435.

Pendiente: ejecutar la defensa en la aplicación con una base de pruebas,
autenticación, micrófono y proveedores configurados. La prueba estática de
avatares del puerto 8765 no verifica ese recorrido. No usar la base de datos
de desarrollo como sustituto de la base dedicada de pruebas.
