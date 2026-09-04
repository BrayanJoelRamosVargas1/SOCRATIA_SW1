# Sprint 3 — Simulación

- Rama P3-A: `feature/simulation-configuration`
- Rama P3-B: `feature/simulation-session-engine`
- Estado: CU12-CU17 texto implementados

## Alcance P3-A

- Configurar una simulación desde un documento propio `PROCESSED` y un banco `READY`.
- Elegir uno de tres perfiles de jurado sembrados idempotentemente.
- Congelar las 12 preguntas del banco como preguntas `BANK`; el modelo admite `FOLLOW_UP` futuro.
- Calibrar cámara, micrófono y detección de persona localmente en el navegador.
- Persistir únicamente los booleanos de disponibilidad y pasar de `DRAFT` a `READY`.

## Alcance P3-B

- CU15 inicia una simulación `READY` de forma idempotente y persiste la primera pregunta.
- El motor de turnos conserva `JURY_TURN`, `WAITING_STUDENT` y `PROCESSING` en PostgreSQL.
- `simulation_turns` guarda el transcript ordenado y evita respuestas duplicadas mediante
  `(simulation_id, client_message_id)` y una barrera única por pregunta respondida.
- CU16 incorpora WebSocket autenticado con cookie HttpOnly, validación estricta de `Origin`,
  heartbeat y reconstrucción de sesión desde la base de datos.
- CU17 permite responder por texto, reconecta con backoff 1-2-4-8-10 segundos y reenvía el mismo
  UUID hasta recibir `answer.accepted`.
- Al terminar las 12 preguntas la simulación continúa `ACTIVE` y reporta
  `questions_exhausted=true`; CU19 decidirá el cierre.

## API

```text
GET    /api/v1/jury-profiles
POST   /api/v1/simulations
GET    /api/v1/simulations
GET    /api/v1/simulations/{id}
PUT    /api/v1/simulations/{id}/calibration
DELETE /api/v1/simulations/{id}
POST   /api/v1/simulations/{id}/start
GET    /api/v1/simulations/{id}/session
WS     /api/v1/ws/simulations/{id}
```

Protocolo P3-B:

```text
server: session.snapshot | jury.question | answer.accepted | session.state | error
client: answer.submit     | heartbeat
```

## Persistencia y despliegue

El administrador de conexiones mantiene únicamente sockets activos. Pregunta actual, secuencia,
progreso, idempotencia y transcript siempre se reconstruyen desde PostgreSQL, por lo que el diseño
es compatible con despliegue detrás de un balanceador en AWS.

## Privacidad

`getUserMedia`, Web Audio y MediaPipe trabajan en el cliente. La API de calibración usa un esquema
cerrado con sólo `camera_ready`, `microphone_ready` y `vision_ready`; payloads con vídeo, audio o
frames son rechazados. P3-B no incorpora todavía STT, TTS, análisis visual ni llamadas LLM live.

## Evidencia

```text
pytest                  75 passed
ruff P3-B               passed
eslint                  passed
next production build   passed
alembic 009 -> 010       passed
Docker smoke             3 respuestas · reconexión en pregunta 4 · retry sin duplicado
```
