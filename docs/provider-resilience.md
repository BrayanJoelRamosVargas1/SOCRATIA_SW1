# Decisión arquitectónica: resiliencia y redundancia de proveedores

**Estado:** adoptada  
**Fecha:** 2026-08-29

## Decisión

Amazon Web Services es la plataforma cloud principal de Socratia. Los contenedores, la red, la
persistencia, los secretos y la observabilidad de producción se diseñan alrededor de AWS. Los
servicios externos se consumen mediante contratos propios y pueden incorporar proveedores
alternativos, pero no sustituyen ni diluyen esa decisión principal.

> Socratia utiliza AWS como plataforma cloud principal. La arquitectura evita dependencias únicas
> mediante abstracciones de proveedores, mecanismos de fallback y redundancia en servicios
> críticos. Los proveedores externos pueden sustituirse ante fallos controlados, mientras AWS
> concentra la infraestructura, persistencia y alta disponibilidad del sistema.

Esta decisión define una dirección incremental. Un proveedor escrito en un diagrama no se considera
implementado hasta que exista su adaptador, configuración, pruebas, telemetría y procedimiento
operativo.

## Límites de responsabilidad

```text
Módulo P1–P6
    ↓ depende de
Contrato de capacidad (EmailProvider, LiveJuryProvider, VectorStoreProvider...)
    ↓ coordinado por
Router de proveedores
    ↓ ejecuta
Adaptadores concretos (Brevo, SES, Groq, Gemini...)
```

- El módulo funcional conoce la capacidad que necesita, nunca el SDK ni la empresa que la ofrece.
- El adaptador traduce el contrato propio hacia una API concreta.
- El router decide orden, timeout, fallback y circuito según la operación.
- La política operativa se configura fuera del código de negocio.
- P6 consume eventos y métricas; no participa en la selección del proveedor.

No se creará una interfaz única y enorme para toda la IA. Las capacidades tienen requisitos
distintos y evolucionarán como contratos separados:

- `DocumentAnalysisProvider`: contexto largo y procesamiento no interactivo.
- `LiveJuryProvider`: baja latencia para conversación en tiempo real.
- `EvaluationProvider`: evaluación estructurada y reproducible.
- `SpeechToTextProvider` y `TextToSpeechProvider`: audio de entrada y salida.
- `EmailProvider`, `StorageProvider` y `VectorStoreProvider`: infraestructura externa.

## Cinco niveles de resiliencia

| Nivel | Mecanismo | Ejemplo | Propietario |
|---|---|---|---|
| 1 | Reintento limitado | un segundo intento con backoff y jitter | router/adaptador |
| 2 | Proveedor alternativo | Groq → Gemini | router de capacidad |
| 3 | Réplica de cómputo | tarea ECS A → tarea ECS B | ECS + ALB |
| 4 | Zona o región alternativa | RDS primary → standby Multi-AZ | AWS |
| 5 | Recuperación multi-cloud | AWS → entorno standby externo | futuro DR |

Los niveles no son intercambiables. La base de datos no tendrá un fallback artesanal hacia otra
instancia sin coordinación, y una copia de archivos fuera de AWS es recuperación ante desastres,
no necesariamente un fallback síncrono de escritura.

## Política de ejecución de proveedores

### Timeout

Toda llamada remota tendrá un timeout explícito y específico de la operación. Las operaciones en
vivo tendrán presupuestos cortos; análisis de documentos y trabajos asíncronos podrán usar límites
mayores. No habrá esperas remotas ilimitadas.

### Reintentos

Se permiten uno o dos reintentos como máximo, con backoff y jitter, únicamente cuando la operación
sea idempotente o tenga una clave de idempotencia. Errores de validación no se reintentan. Un timeout
de correo puede tener resultado ambiguo; no se enviará automáticamente un duplicado mediante otro
proveedor sin una política de idempotencia o una confirmación de fallo definitivo.

### Circuit breaker

Cada combinación capacidad/proveedor mantiene un circuito independiente:

```text
CLOSED ── fallos consecutivos ──> OPEN
  ▲                                │
  └──── prueba exitosa <── HALF_OPEN
```

Con el circuito abierto, el router omite temporalmente el proveedor fallido. Los umbrales y tiempos
se decidirán con métricas reales, no se fijarán arbitrariamente antes de implementar la capacidad.

### Clasificación de fallos

Los adaptadores normalizan al menos: `timeout`, `rate_limit`, `quota`, `authentication`,
`provider_5xx`, `invalid_request` y `unknown`. El router solo usa fallback cuando la semántica de la
operación lo permite. Un error contractual local no debe provocar una cascada inútil por todos los
proveedores.

## Enrutamiento por capacidad

La tabla expresa el orden objetivo, no el estado actual de implementación:

| Capacidad | Orden objetivo | Motivo |
|---|---|---|
| Jurado en vivo | Groq → Gemini → OpenAI | prioriza latencia |
| Análisis documental | Gemini → OpenAI → Groq | contexto largo y trabajo asíncrono |
| Evaluación final | Gemini/OpenAI → Groq | estructura y calidad antes que latencia |
| STT | Groq Whisper → OpenAI Whisper → Azure Speech | transcripción rápida y alternativa compatible |
| TTS | ElevenLabs → Amazon Polly → Azure Speech | calidad inicial y fallback dentro de AWS |
| Correo | Brevo SMTP → Amazon SES | proveedor transaccional actual y alternativa AWS |
| Vectores | Pinecone → PostgreSQL/pgvector | servicio especializado y ruta recuperable en RDS |
| Archivos | Amazon S3; copia futura GCS/R2 | S3 es primario; la copia externa es DR |

Un fallback vectorial solo será automático si ambos índices están sincronizados o pueden
reconstruirse dentro del objetivo de recuperación. Hasta entonces, pgvector es una estrategia de
continuidad, no una réplica activa. La misma distinción aplica a S3 frente a copias externas.

## Observabilidad

Cada llamada externa emitirá una observación estructurada, sin credenciales, tokens, documentos ni
prompts completos:

```text
capability
operation
provider
outcome
fallback_used
latency_ms
failure_class
circuit_state
correlation_id
occurred_at
```

P6 podrá presentar disponibilidad, latencia, errores, circuitos y porcentaje de fallbacks por
proveedor. El costo y la cuota formarán parte del router cuando existan datos fiables; nunca se
elegirá un proveedor más barato si incumple privacidad, calidad o disponibilidad requeridas.

## AWS como núcleo

El objetivo de producción es:

```text
Route 53
   ↓
Application Load Balancer
   ↓
ECS Fargate en al menos dos AZ
   ├── Frontend Next.js
   └── Backend FastAPI
          ├── RDS PostgreSQL Multi-AZ
          ├── Amazon S3
          ├── Secrets Manager
          └── CloudWatch
```

RDS administra la réplica y el failover de la base relacional. ALB distribuye tráfico entre tareas
saludables. Las credenciales de proveedores se inyectan en ECS desde Secrets Manager y no se
incluyen en imágenes ni repositorios.

## Entrega incremental

| Fase | Implementar | Solo mantener diseñado |
|---|---|---|
| Actual | SMTP/Brevo y CU09 con Gemini Embedding + Pinecone | SES y pgvector como fallbacks |
| P2 siguiente | S3, retrieval RAG y proveedor generativo | proveedor LLM alternativo |
| P3 | Groq para jurado/STT y ElevenLabs | Gemini/OpenAI, Polly/Azure |
| Endurecimiento | routers, métricas, circuit breakers y fallbacks probados | multi-cloud |
| DR futuro | procedimientos multi-región/multi-cloud medidos | — |

## Fuentes técnicas

- [Compatibilidad OpenAI de Groq](https://console.groq.com/docs/openai)
- [Speech-to-Text de Groq](https://console.groq.com/docs/speech-to-text)
- [Conexión SMTP cifrada con Amazon SES](https://docs.aws.amazon.com/ses/latest/dg/smtp-connect.html)
- [Failover Multi-AZ de Amazon RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.Failover.html)
- [Balanceo de servicios ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-load-balancing.html)
- [Secretos en contenedores ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specifying-sensitive-data.html)
