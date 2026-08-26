# Arquitectura de Socratia

## Decisión congelada

Socratia se implementa como SaaS web en un monorepo. El backend es un monolito modular FastAPI, el frontend usa Next.js y PostgreSQL almacena los datos relacionales. Docker Compose ejecuta el entorno local. En producción, los contenedores se alojarán en AWS, PostgreSQL migrará a RDS y los documentos a S3. Pinecone y los proveedores de IA entrarán en sprints posteriores. MediaPipe se ejecutará en el navegador y enviará únicamente métricas al backend.

## Regla de dependencias

```text
auth -> users
documents -> storage -> rag -> vector_db -> questions
questions -> simulations -> voice | vision | evaluation -> reports
payments -> subscriptions
admin -> servicios administrativos
todos -> audit
```

Un módulo expone sus operaciones mediante su servicio y sus esquemas. Ningún router accede directamente a las tablas de otro módulo. Las llamadas a proveedores externos viven bajo `app/integrations`.

## Estructura interna de un módulo

```text
router.py      HTTP y serialización
schemas.py     contratos Pydantic
models.py      persistencia SQLAlchemy
repository.py  consultas a PostgreSQL
service.py     reglas de negocio
exceptions.py  errores del dominio
```

El Sprint 1 implementa esta estructura en `auth` y `users`. Los demás directorios reservan límites explícitos, sin añadir SDK ni código especulativo.

## Autenticación

1. Registro o login valida las credenciales.
2. El backend crea un JWT de acceso de corta duración.
3. Crea un refresh token opaco y guarda sólo su SHA-256 en `sessions`.
4. Ambos valores viajan en cookies `HttpOnly`.
5. La renovación rota el refresh token y revoca la sesión anterior.
6. Logout revoca la sesión vigente y elimina ambas cookies.

## Próximos incrementos

1. Documentos, S3, RAG y preguntas.
2. Simulación, WebSocket y voz.
3. MediaPipe, evaluación y reportes.
4. Suscripciones, pagos, administración, auditoría y despliegue AWS.

