# P2 — Gestión de documentos y preparación

Este módulo implementa los casos iniciales de Sprint 2:

- CU06: cargar PDF/DOCX.
- CU07: listar y consultar documentos propios.
- CU08: consultar estado e historial de procesamiento.
- Eliminar un documento propio.

## Dependencias

```text
router -> service -> repository -> PostgreSQL
                   -> StorageProvider -> LocalStorageProvider
```

`DocumentService` no conoce S3. El adaptador local persiste archivos en un volumen Docker y será sustituible por `S3StorageProvider` sin cambiar las reglas del módulo.

## Seguridad

`DocumentPolicy` exige que `document.user_id == current_user.id`. Una consulta sobre un documento ajeno responde `404` para no revelar que el identificador existe.

## Alcance pendiente

- Procesamiento de texto.
- Chunking y embeddings.
- Pinecone y RAG.
- Banco de preguntas.
- Material de exposición.

