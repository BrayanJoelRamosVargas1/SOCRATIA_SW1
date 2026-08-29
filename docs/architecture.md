# Arquitectura de Socratia

## Decisión congelada

Socratia se implementa como SaaS web en un monorepo. El backend es un monolito modular FastAPI,
el frontend usa Next.js y PostgreSQL almacena los datos relacionales. Docker Compose ejecuta el
entorno local. En producción, los contenedores se alojarán en AWS, PostgreSQL migrará a RDS y los
documentos a S3. Pinecone y los proveedores de IA entrarán en sprints posteriores. MediaPipe se
ejecutará en el navegador y enviará únicamente métricas al backend.

Los límites funcionales del backend reflejan los seis paquetes y los 37 casos de uso del modelo
UML:

```text
backend/app/modules/
├── p1_gestion_identidad_seguridad/       CU01–CU05
├── p2_gestion_documentos_preparacion/    CU06–CU11
├── p3_gestion_simulacion/                 CU12–CU19
├── p4_gestion_evaluacion_resultados/      CU20–CU27
├── p5_gestion_saas/                       CU28–CU31
└── p6_gestion_administracion/             CU32–CU37
```

Los nombres UML conservan el formato `P1_GestionIdentidadSeguridad`; los paquetes Python usan
minúsculas y guiones bajos para ser portables en Linux.

## Regla de dependencias

```text
API v1 -> rutas de P1 y P2
P2 -> política de usuario autenticado de P1
P2 -> StorageProvider
P2 -> P3 -> P4
P5 -> proveedor de pagos
P6 -> contratos administrativos explícitos de P1–P5
```

Un paquete expone sus operaciones mediante servicios, esquemas y rutas. Ninguna ruta accede
directamente a las tablas de otro paquete. Una dependencia entre paquetes debe ser explícita y no
puede saltarse las reglas del paquete propietario.

`app/api/v1/router.py` sólo compone los routers de los paquetes; no contiene reglas de negocio.

## Estructura interna de un paquete implementado

```text
routes/          HTTP, dependencias y serialización
schemas/         contratos Pydantic
models/          persistencia SQLAlchemy
repositories/    consultas a PostgreSQL
services/        reglas de aplicación y negocio
policies/        autorización sobre recursos
exceptions.py    errores del dominio
README.md        alcance, CU, dependencias y estado
```

Las funciones de FastAPI en `routes/` cumplen también el papel de controlador mientras la
orquestación sea pequeña. Una carpeta `controllers/` se añadirá cuando exista lógica de
coordinación que no pertenezca ni al transporte HTTP ni al servicio de aplicación.

P1 y P2 contienen las capas que utilizan actualmente. P3–P6 sólo contienen `README.md` y
`__init__.py` hasta que sus casos de uso sean implementados.

## Integraciones compartidas

Los proveedores externos permanecen fuera de P1–P6:

```text
app/integrations/
├── email/
├── llm/
├── payments/
├── storage/
├── stt/
├── tts/
└── vector_db/
```

Una integración puede servir a varios paquetes y no contiene reglas funcionales del negocio.

## AWS y resiliencia de proveedores

AWS es el cloud principal, no un proveedor intercambiable más. La producción se proyecta sobre
Route 53, ALB, ECS Fargate, RDS PostgreSQL Multi-AZ, S3, Secrets Manager y CloudWatch. La alta
disponibilidad de cómputo y base de datos pertenece a esa infraestructura administrada.

Las capacidades externas dependen de contratos propios. Cuando una capacidad justifique más de un
adaptador, un router aplicará timeout, reintentos limitados, circuit breaker, fallback seguro y
telemetría. La selección podrá variar según la operación: jurado en vivo, análisis documental y
evaluación no comparten necesariamente el mismo orden de proveedores.

La regla completa, sus cinco niveles y el estado incremental se definen en
[`docs/provider-resilience.md`](provider-resilience.md). Ningún fallback descrito allí debe
presentarse como implementado antes de contar con código, pruebas, telemetría y operación real.

## Autenticación

1. Registro o login valida las credenciales.
2. El backend crea un JWT de acceso de corta duración.
3. Crea un refresh token opaco y guarda sólo su SHA-256 en `sessions`.
4. Ambos valores viajan en cookies `HttpOnly`.
5. La renovación rota el refresh token y revoca la sesión anterior.
6. Logout revoca la sesión vigente y elimina ambas cookies.

## Próximos incrementos

1. Completar P2: procesamiento, S3, RAG y preguntas.
2. Implementar P3: simulación, WebSocket y voz.
3. Implementar P4: MediaPipe, evaluación y reportes.
4. Implementar P5 y P6: suscripciones, pagos, administración y auditoría.
5. Desplegar los contenedores y servicios administrados en AWS.
