# Socratia

Socratia es un SaaS web para preparar y simular defensas académicas. Este repositorio contiene el primer incremento funcional sobre la arquitectura acordada: **Next.js + FastAPI + monolito modular + PostgreSQL + Docker**. El backend agrupa sus 37 casos de uso en seis paquetes funcionales P1–P6, alineados con el modelo UML.

## Estado del producto

Sprint 1 está congelado en `v0.1.0-sprint1`. La primera mitad de Sprint 2 añade gestión segura de documentos:

- API versionada en `/api/v1` y documentación OpenAPI en `/docs`.
- Registro, inicio de sesión, renovación y cierre de sesión.
- Access token corto y refresh session opaca, rotatoria y revocable.
- Usuarios, roles y perfil editable.
- Landing, registro, login y dashboard protegido.
- SQLAlchemy 2, Alembic y PostgreSQL.
- Pruebas automatizadas del flujo de autenticación.
- Carga de PDF/DOCX de hasta 20 MB.
- Listado, detalle, estado y eliminación de documentos propios.
- Autorización por propietario sin filtración de identificadores ajenos.
- Archivos persistentes en un volumen Docker mediante `StorageProvider` sustituible por S3.
- Paquetes funcionales P1–P6 visibles en `backend/app/modules`.

RAG, Pinecone, preguntas, voz, visión, evaluación y pagos quedan delimitados en la arquitectura, pero se implementarán en incrementos posteriores.

## Inicio rápido con Docker

Requisitos: Docker Desktop con Docker Compose.

```bash
cp .env.example .env
docker compose up --build
```

En PowerShell, el primer comando equivalente es:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Servicios:

- Aplicación web: http://localhost:3000
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- PostgreSQL: `localhost:5432`

Los volúmenes `postgres_data` y `document_files` conservan metadata y archivos al reiniciar los contenedores.

Para desarrollo con recarga automática:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

## Desarrollo sin Docker

Backend (Python 3.12 recomendado):

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend (Node.js 22 LTS recomendado):

```bash
cd frontend
npm install
npm run dev
```

## Pruebas

```bash
cd backend
pytest
```

```bash
cd frontend
npm run lint
npm run build
```

## Decisiones de seguridad

Los tokens se entregan en cookies `HttpOnly`; no se guardan credenciales en `localStorage`. El access token expira pronto. El refresh token es aleatorio, se persiste únicamente como hash, rota al renovarse y se revoca al cerrar sesión. En producción se debe usar HTTPS, `COOKIE_SECURE=true`, un `JWT_SECRET` aleatorio y orígenes CORS explícitos.

Las contraseñas nuevas requieren al menos 15 caracteres, permiten frases y espacios y no imponen
mezclas artificiales de mayúsculas/números/símbolos. Los espacios al inicio o al final se conservan
exactamente y el formulario lo advierte antes del envío. FastAPI rechaza claves predecibles y Argon2
protege su almacenamiento.

Cada operación de documentos valida además la propiedad del recurso. Un usuario no puede consultar, procesar ni eliminar documentos de otra cuenta. PostgreSQL guarda metadata y una clave de almacenamiento; nunca guarda los bytes del archivo.

## Documentación

- [Arquitectura y límites modulares](docs/architecture.md)
- [Mapa de paquetes P1–P6](backend/app/modules/README.md)
- [Política de contraseñas y UX](docs/security/password-policy.md)
- [C4: contexto](docs/c4/context.md)
- [C4: contenedores](docs/c4/containers.md)
- [C4: componentes del backend](docs/c4/backend-components.md)
- [Sprint 1: cierre](docs/sprints/sprint-01.md)
- [Sprint 2: documentos](docs/sprints/sprint-02.md)
