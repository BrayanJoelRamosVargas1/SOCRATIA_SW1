# AWS — infraestructura principal

AWS es la plataforma cloud oficial de Socratia. Este directorio alojará la infraestructura como
código cuando comience el sprint de despliegue; actualmente no contiene recursos desplegables ni
debe presentarse como un entorno ya provisionado.

## Topología objetivo

```text
Route 53
   ↓
Application Load Balancer público
   ├── /api/*  → servicio ECS Fargate backend (mínimo 2 tareas)
   └── /*      → servicio ECS Fargate frontend (mínimo 2 tareas)
                    │
                    └── backend
                          ├── RDS PostgreSQL Multi-AZ
                          ├── Amazon S3
                          ├── AWS Secrets Manager
                          └── CloudWatch Logs/Metrics/Alarms
```

Las tareas se distribuyen entre al menos dos zonas de disponibilidad. RDS administra el failover
relacional; no se implementará conmutación artesanal hacia otra base. ECR conserva las imágenes de
frontend y backend. Secrets Manager entrega `DATABASE_URL`, `JWT_SECRET`, credenciales SMTP y demás
claves al runtime de ECS.

## Límites

- AWS resuelve cómputo, red, persistencia, secretos, observabilidad y alta disponibilidad.
- Los routers en `app/integrations` resuelven proveedores funcionales como LLM, voz o correo.
- Amazon SES puede ser fallback de Brevo, pero no convierte el sistema en “multi-cloud principal”.
- GCP u otro cloud se evaluará únicamente como recuperación ante desastres posterior.

Véase [`docs/provider-resilience.md`](../../docs/provider-resilience.md).
