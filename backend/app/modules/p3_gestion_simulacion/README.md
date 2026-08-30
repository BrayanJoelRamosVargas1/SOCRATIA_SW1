# P3 — Gestión de simulación

Casos de uso: **CU12–CU19**.

## Responsabilidad

Crear y ejecutar simulaciones de defensa, coordinar el jurado virtual y gestionar la interacción
por voz durante una práctica.

## Dependencias

- P2 para documentos, contexto y preguntas preparadas.
- P1 para el usuario autenticado.
- P2 sólo mediante documentos procesados y bancos READY; P3 congela 12 preguntas por simulación.
- MediaPipe y Web Audio se ejecutan localmente en el navegador durante CU14.
- `LLMProvider`, `STTProvider` y `TTSProvider` se incorporarán en P3-B/P3-C.

## No permitido

- Administrar usuarios, suscripciones o pagos.
- Ser propietario de las reglas de evaluación y reportes finales.

## P3-A — implementado

- CU12: crear, listar, consultar y eliminar configuraciones DRAFT/READY.
- CU13: perfiles metodológico, técnico y crítico con bootstrap idempotente.
- CU14: comprobación local de cámara, nivel de micrófono y detección de persona.
- Máquina de estados explícita y selección congelada de preguntas BANK/FOLLOW_UP.
- El backend sólo recibe booleanos de disponibilidad; no almacena frames ni audio.

P3-B añadirá inicio, motor de sesión, turnos y WebSocket sin modificar esta frontera.
