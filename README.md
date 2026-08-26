# Socratia

Socratia es un SaaS web para preparar y simular defensas académicas. Este repositorio contiene el primer incremento funcional sobre la arquitectura acordada: **Next.js + FastAPI + monolito modular + PostgreSQL + Docker**.

## Estado del Sprint 1

- API versionada en `/api/v1` y documentación OpenAPI en `/docs`.
- Registro, inicio de sesión, renovación y cierre de sesión.
- Access token corto y refresh session opaca, rotatoria y revocable.
- Usuarios, roles y perfil editable.
- Landing, registro, login y dashboard protegido.
- SQLAlchemy 2, Alembic y PostgreSQL.
- Pruebas automatizadas del flujo de autenticación.

Las integraciones de documentos, RAG, voz, visión, evaluación y pagos quedan delimitadas en la arquitectura, pero se implementarán en sprints posteriores.

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

## Documentación

- [Arquitectura y límites modulares](docs/architecture.md)
- [C4: contexto](docs/c4/context.md)
- [C4: contenedores](docs/c4/containers.md)
- [C4: componentes del backend](docs/c4/backend-components.md)
