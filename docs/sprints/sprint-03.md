# Sprint 3 — Simulación

- Rama P3-A: `feature/simulation-configuration`
- Estado: CU12-CU14 implementados

## Alcance P3-A

- Configurar una simulación desde un documento propio `PROCESSED` y un banco `READY`.
- Elegir uno de tres perfiles de jurado sembrados idempotentemente.
- Congelar las 12 preguntas del banco como preguntas `BANK`; el modelo admite `FOLLOW_UP` futuro.
- Calibrar cámara, micrófono y detección de persona localmente en el navegador.
- Persistir únicamente los booleanos de disponibilidad y pasar de `DRAFT` a `READY`.

## API

```text
GET    /api/v1/jury-profiles
POST   /api/v1/simulations
GET    /api/v1/simulations
GET    /api/v1/simulations/{id}
PUT    /api/v1/simulations/{id}/calibration
DELETE /api/v1/simulations/{id}
```

## Privacidad

`getUserMedia`, Web Audio y MediaPipe trabajan en el cliente. La API de calibración usa un esquema
cerrado con sólo `camera_ready`, `microphone_ready` y `vision_ready`; payloads con vídeo, audio o
frames son rechazados. No se calcula aún una nota de postura o contacto visual.

## Evidencia

```text
pytest                  70 passed
ruff                    passed
eslint                  passed
next production build   passed
alembic 001 -> 009       passed
Docker smoke             DRAFT -> READY · 12 preguntas · Jurado Técnico
```

P3-B incorporará CU15 y la base de CU16/CU17: motor de sesión, turnos y WebSocket.
