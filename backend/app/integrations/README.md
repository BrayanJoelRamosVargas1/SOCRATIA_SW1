# Adaptadores externos

Los módulos P1–P6 dependen de capacidades definidas aquí, nunca de SDK o empresas concretas. Esta
carpeta contiene contratos, adaptadores y, cuando haya más de un proveedor real, routers de
selección y fallback.

## Reglas

1. El contrato expresa una capacidad del producto, no la forma de una API externa.
2. Un adaptador encapsula autenticación, serialización, timeout y traducción de errores.
3. Un router solo se añade cuando existen al menos dos adaptadores utilizables o una necesidad de
   enrutamiento ya aprobada; no se crean fallbacks ficticios.
4. Reintentos, fallback y circuit breaker respetan idempotencia y resultado ambiguo.
5. Toda ejecución externa emitirá telemetría sin secretos ni contenido académico sensible.
6. Las credenciales llegan por configuración local ignorada o AWS Secrets Manager; nunca se
   escriben en código, imágenes o archivos versionados.

## Estado

| Capacidad | Estado actual | Siguiente adaptador | Respaldo objetivo |
|---|---|---|---|
| Email | `EmailProvider` + SMTP/Brevo | Amazon SES | Brevo → SES |
| Storage | `StorageProvider` + filesystem local | Amazon S3 | copia externa futura |
| Embeddings | `EmbeddingProvider` + Gemini Embedding 2 | evaluar calidad 768/1536 | modelo alternativo futuro |
| LLM | reservado | Gemini generativo en CU10 | rutas por operación |
| Vector DB | `VectorStoreProvider` + Pinecone serverless | retrieval de CU10 | PostgreSQL/pgvector |
| STT | reservado | Groq Whisper en P3 | OpenAI/Azure |
| TTS | reservado | ElevenLabs en P3 | Amazon Polly/Azure |
| Payments | reservado | se decide en P5 | se decide en P5 |

La estrategia adoptada está en
[`docs/provider-resilience.md`](../../../docs/provider-resilience.md). AWS permanece como
infraestructura principal; esta capa resuelve dependencias externas, no el failover de RDS, ECS o
zonas de disponibilidad.
