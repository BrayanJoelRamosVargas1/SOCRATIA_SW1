# Sprint 2 — Documentos y preparación

- Rama funcional de origen: `feature/documents`
- Rama del refactor arquitectónico: `refactor/modular-use-case-packages`
- Estado: primera mitad implementada

## Objetivo del incremento

Completar el recorrido login → mis documentos → cargar → listar → consultar detalle/estado → eliminar, manteniendo aislamiento estricto entre usuarios.

## Casos cubiertos

- CU06: cargar documento PDF o DOCX.
- CU07: listar y consultar documentos propios.
- CU08: consultar estado e historial de procesamiento.
- Eliminación segura del archivo y su metadata.

## API

```text
POST   /api/v1/documents
GET    /api/v1/documents
GET    /api/v1/documents/{id}
GET    /api/v1/documents/{id}/status
DELETE /api/v1/documents/{id}
```

## Persistencia

PostgreSQL almacena `documents` y `document_processing`. Los bytes viven detrás de `StorageProvider`; durante esta fase, `LocalStorageProvider` escribe de forma atómica en el volumen Docker `document_files`. La clave sigue el formato:

```text
users/{user_id}/documents/{document_id}/{document_id}.{extension}
```

El cambio futuro a S3 no modifica routers, servicios, repositorios ni policies.

## Ubicación arquitectónica

Los casos CU06–CU11 pertenecen a
`backend/app/modules/p2_gestion_documentos_preparacion`. La autenticación requerida por sus rutas
se consume desde la política pública de P1. Los adaptadores de almacenamiento y los futuros
proveedores de vectores/LLM permanecen en `app/integrations`.

## Reglas implementadas

- Sólo PDF y DOCX con tipo MIME y firma interna válidos.
- Tamaño máximo configurable, 20 MB por defecto.
- Nombres saneados y claves generadas por el servidor.
- No se exponen rutas internas ni `storage_key` en la API.
- Toda consulta verifica `document.user_id == current_user.id`.
- Los IDs ajenos responden `404` para no filtrar su existencia.
- Si falla PostgreSQL después de guardar, el archivo se elimina como compensación.

## Pruebas

```text
test_upload_document
test_list_own_documents
test_cannot_read_other_user_document
test_get_processing_status
test_reject_invalid_file
test_delete_document
```

Evidencia actual:

```text
pytest                         10 passed
ruff                           passed
eslint                         passed
next production build          passed
alembic 001 -> 002 -> 003       passed
POST /documents                HTTP 201
GET ajeno                      HTTP 404
GET después de recrear backend HTTP 200
DELETE /documents/{id}         HTTP 204
frontend /documents            HTTP 200
```

## Pendiente en Sprint 2

- `POST /documents/{id}/process`.
- Extracción de texto, chunking y embeddings.
- S3 y Pinecone.
- Generación y consulta del banco de preguntas.
- Material de exposición.
