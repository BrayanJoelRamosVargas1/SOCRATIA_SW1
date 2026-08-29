# Sprint 2 — Documentos y preparación

- Rama funcional de CU09: `feature/document-processing`
- Rama del refactor arquitectónico: `refactor/modular-use-case-packages`
- Estado: CU06-CU09 implementados

## Objetivo del incremento

Completar el recorrido login → documentos → carga → procesamiento semántico → estado → eliminación, manteniendo aislamiento estricto entre usuarios.

## Casos cubiertos

- CU06: cargar documento PDF o DOCX.
- CU07: listar y consultar documentos propios.
- CU08: consultar estado e historial de procesamiento.
- CU09: extraer, normalizar, fragmentar, vectorizar e indexar un documento.
- Eliminación segura del archivo y su metadata.

## API

```text
POST   /api/v1/documents
POST   /api/v1/documents/{id}/process
GET    /api/v1/documents
GET    /api/v1/documents/{id}
GET    /api/v1/documents/{id}/status
DELETE /api/v1/documents/{id}
```

## Persistencia

PostgreSQL almacena `documents`, `document_processing` y `document_chunks`. Los bytes viven detrás de `StorageProvider`; durante esta fase, `LocalStorageProvider` escribe de forma atómica en el volumen Docker `document_files`. La clave sigue el formato:

```text
users/{user_id}/documents/{document_id}/{document_id}.{extension}
```

El cambio futuro a S3 no modifica routers, servicios, repositorios ni policies. Los embeddings se generan con Gemini Embedding 2 en 768 dimensiones y Pinecone almacena vectores por namespace de usuario. El texto de cada chunk permanece también en PostgreSQL como fuente de verdad para CU10.

## Ubicación arquitectónica

Los casos CU06–CU11 pertenecen a
`backend/app/modules/p2_gestion_documentos_preparacion`. La autenticación requerida por sus rutas
se consume desde la política pública de P1. Los adaptadores de almacenamiento, embeddings y
vectores permanecen en `app/integrations`; el proveedor generativo de CU10 todavía no se implementa.

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
```

Evidencia actual:

```text
pytest                         40 passed
ruff                           passed
eslint                         passed
next production build          passed
alembic 001 -> 006              passed
POST /documents                HTTP 201
POST /documents/{id}/process   HTTP 200 (Gemini + Pinecone reales)
GET ajeno                      HTTP 404
GET después de recrear backend HTTP 200
DELETE /documents/{id}         HTTP 204
frontend /documents            HTTP 200
```

## Pendiente en Sprint 2

- S3 como adaptador de almacenamiento de producción.
- Retrieval RAG sobre los vectores ya indexados.
- Generación y consulta del banco de preguntas.
- Material de exposición.
