# P2 — Gestión de documentos y preparación

Casos de uso: **CU06–CU11**.

## Casos de uso

- CU06: cargar documento.
- CU07: consultar documento.
- CU08: consultar estado de procesamiento.
- CU09: procesar documento.
- CU10: generar banco de preguntas.
- CU11: generar material de exposición.

## Responsabilidad

Gestionar documentos académicos y preparar el conocimiento que utilizarán las simulaciones.
P2 es propietario de las tablas `documents`, `document_processing`, `document_chunks`,
`question_banks` y `questions`.

## Capas implementadas

```text
routes -> services -> repositories -> PostgreSQL
                   -> StorageProvider -> LocalStorageProvider
                   -> EmbeddingProvider -> GeminiEmbeddingProvider
                   -> VectorStoreProvider -> PineconeVectorStoreProvider
                   -> LLMRouter -> GeminiQuestionProvider
                                -> GroqQuestionProvider (fallback)
   |          |
schemas    models
   |
policies
```

En esta fase, las funciones de FastAPI en `routes/` cumplen también la responsabilidad de
controlador. Una capa `controllers/` separada se añadirá únicamente cuando la orquestación lo
requiera.

## Dependencias permitidas

- P1 para obtener el usuario autenticado.
- `StorageProvider` para los archivos.
- `EmbeddingProvider` para convertir chunks en vectores.
- `VectorStoreProvider` para indexar, consultar y eliminar vectores.
- `LLMProvider` para generar salidas estructuradas de CU10 y CU11.

## No permitido

- Gestionar usuarios o pagos.
- Ejecutar una simulación.
- Evaluar una defensa.

## Seguridad

`DocumentPolicy` exige que `document.user_id == current_user.id`. Una consulta sobre un
documento ajeno responde `404` para no revelar que el identificador existe.

## Estado

CU06-CU11 y la eliminación segura están implementados. CU09 extrae PDF/DOCX, normaliza,
fragmenta, genera embeddings Gemini y escribe en Pinecone. CU10 recupera evidencia mediante seis
intenciones, genera exactamente 12 preguntas estructuradas y persiste la trazabilidad interna. Usa
Gemini como proveedor primario, Groq como fallback y circuit breakers independientes. El material
CU11 reutiliza el mismo retrieval y resiliencia para producir una exposición ajustada a la duración.
S3 queda como cambio de infraestructura posterior; P2 está funcionalmente completo.
