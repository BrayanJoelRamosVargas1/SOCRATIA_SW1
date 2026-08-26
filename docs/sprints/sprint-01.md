# Sprint 1 — Incremento entregado

Fecha de cierre: 2026-08-26  
Versión: `v0.1.0-sprint1`

## Objetivo

Construir el esqueleto operativo de Socratia y completar el recorrido registro → login → dashboard → logout sobre la arquitectura real del producto.

## Entregado

- Docker Compose operativo con frontend, backend y PostgreSQL.
- Frontend Next.js con landing, registro, login y dashboard protegido.
- Backend FastAPI con API versionada y documentación OpenAPI.
- PostgreSQL, SQLAlchemy 2 y migraciones Alembic.
- Registro, login, refresh rotatorio, logout y perfil.
- Usuarios y rol inicial de estudiante.
- Cookies HttpOnly y contraseñas con Argon2.
- Refresh tokens almacenados únicamente como hash y revocables.
- Pruebas automatizadas del backend.
- Ruff y ESLint sin errores.
- Build de producción del frontend.
- Smoke test completo sobre Docker Compose.

## Evidencia de cierre

```text
pytest             3 passed
ruff               passed
eslint             passed
next build         passed
alembic upgrade    passed
frontend /         HTTP 200
backend /health    HTTP 200
backend /docs      HTTP 200
auth smoke test    passed
```

## Fuera de alcance

Documentos, S3, RAG, preguntas, simulación, voz, visión, evaluación, pagos y despliegue AWS pertenecen a incrementos posteriores.

