# Sprint 2 — Documentos y preparación

- Rama funcional de CU09: `feature/document-processing`
- Rama funcional de CU10: `feature/question-bank-rag`
- Rama del refactor arquitectónico: `refactor/modular-use-case-packages`
- Estado: CU06-CU10 implementados

## Objetivo del incremento

Completar el recorrido login → documentos → carga → procesamiento semántico → banco de preguntas, manteniendo aislamiento estricto entre usuarios.

## Casos cubiertos

- CU06: cargar documento PDF o DOCX.
- CU07: listar y consultar documentos propios.
- CU08: consultar estado e historial de procesamiento.
- CU09: extraer, normalizar, fragmentar, vectorizar e indexar un documento.
- CU10: recuperar evidencia y generar/consultar un banco de preguntas.
- Eliminación segura del archivo y su metadata.

## API

```text
POST   /api/v1/documents
POST   /api/v1/documents/{id}/process
GET    /api/v1/documents
GET    /api/v1/documents/{id}
GET    /api/v1/documents/{id}/status
POST   /api/v1/documents/{id}/questions/generate
GET    /api/v1/documents/{id}/questions
DELETE /api/v1/documents/{id}
```

## Persistencia

PostgreSQL almacena `documents`, `document_processing`, `document_chunks`, `question_banks` y
`questions`. Los bytes viven detrás de `StorageProvider`; durante esta fase,
`LocalStorageProvider` escribe de forma atómica en el volumen Docker `document_files`. La clave
sigue el formato:

```text
users/{user_id}/documents/{document_id}/{document_id}.{extension}
```

El cambio futuro a S3 no modifica routers, servicios, repositorios ni policies. Los embeddings se generan con Gemini Embedding 2 en 768 dimensiones y Pinecone almacena vectores por namespace de usuario. El texto de cada chunk permanece también en PostgreSQL como fuente de verdad para CU10.

## Ubicación arquitectónica

Los casos CU06–CU11 pertenecen a
`backend/app/modules/p2_gestion_documentos_preparacion`. La autenticación requerida por sus rutas
se consume desde la política pública de P1. Los adaptadores de almacenamiento, embeddings,
vectores y LLM permanecen en `app/integrations`. CU10 enruta Gemini 2.5 Flash como proveedor
primario y Groq GPT-OSS 20B como fallback.

## Reglas implementadas

- Sólo PDF y DOCX con tipo MIME y firma interna válidos.
- Tamaño máximo configurable, 20 MB por defecto.
- Nombres saneados y claves generadas por el servidor.
- No se exponen rutas internas ni `storage_key` en la API.
- Toda consulta verifica `document.user_id == current_user.id`.
- Los IDs ajenos responden `404` para no filtrar su existencia.
- Si falla PostgreSQL después de guardar, el archivo se elimina como compensación.
- El DOCX limita también su tamaño descomprimido para reducir riesgo de zip bombs.
- Cada proceso registra `EXTRACTION`, `CHUNKING`, `EMBEDDING`, `VECTOR_STORE` y `COMPLETE`.
- Un fallo deja el documento en `ERROR` y permite reintento sin duplicar vectores.
- Los IDs vectoriales son determinísticos y la eliminación limpia Pinecone antes de borrar metadata.
- Las seis búsquedas de CU10 filtran por `user_id` y `document_id`, además de revalidar metadata.
- El contrato exige exactamente 12 preguntas: tres conceptuales, tres metodológicas, tres críticas
  y tres aplicadas, con dificultad media o alta.
- La API pública oculta puntos esperados y chunks fuente; esa trazabilidad queda en PostgreSQL.
- Sólo un `POST` explícito genera o regenera; el `GET` consulta exclusivamente la base de datos.
- Si ambos LLM fallan, CU10 devuelve `QUESTION_GENERATION_FAILED` sin dañar el documento procesado
  ni reemplazar un banco válido anterior.

## Pruebas

```text
test_upload_document
test_list_own_documents
test_cannot_read_other_user_document
test_get_processing_status
test_reject_invalid_file
test_delete_document
test_process_docx_with_embeddings_and_vectors
test_process_pdf
test_processing_provider_failure_is_recorded
test_cannot_process_other_user_document
test_delete_processed_document_removes_vectors
test_reprocess_document_reuses_deterministic_vector_ids
test_reject_document_without_extractable_text
test_reject_second_processing_while_active
test_question_bank_primary_provider
test_question_bank_fallback_paths
test_question_bank_retrieval_filters_and_deduplication
test_question_bank_public_contract_hides_internal_answers
test_question_bank_regeneration_and_cascade_delete
test_question_provider_circuit_breaker
```

Evidencia actual:

```text
pytest                         52 passed
ruff                           passed
eslint                         passed
next production build          passed
alembic 001 -> 007              passed
POST /documents                HTTP 201
POST /documents/{id}/process   HTTP 200 (Gemini + Pinecone reales)
POST /questions/generate       HTTP 200 (Gemini real)
fallback Gemini -> Groq        HTTP 200 (Groq real)
GET /questions                 12 preguntas persistidas
GET ajeno                      HTTP 404
GET después de recrear backend HTTP 200
DELETE /documents/{id}         HTTP 204
frontend /documents            HTTP 200
```

## Pendiente en Sprint 2

- S3 como adaptador de almacenamiento de producción.
- Material de exposición.
