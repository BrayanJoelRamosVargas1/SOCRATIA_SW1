# C4 — Nivel 1: contexto

```mermaid
C4Context
  title Contexto de Socratia
  Person(student, "Estudiante", "Prepara y practica una defensa académica")
  Person(admin, "Administrador", "Gestiona la plataforma")
  System(socratia, "Socratia sobre AWS", "Genera preguntas, ejecuta simulaciones y entrega evaluación")
  System_Ext(ai, "Proveedores externos redundantes", "LLM, STT, TTS y correo detrás de contratos propios")
  System_Ext(aws, "Servicios administrados AWS", "ECS, RDS Multi-AZ, S3, Secrets Manager y observabilidad")
  System_Ext(payments, "Proveedor de pagos", "Cobros y confirmaciones")

  Rel(student, socratia, "Usa", "HTTPS / WebSocket")
  Rel(admin, socratia, "Administra", "HTTPS")
  Rel(socratia, ai, "Solicita capacidades mediante provider routers")
  Rel(socratia, aws, "Ejecuta y persiste")
  Rel(socratia, payments, "Procesa suscripciones")
```
