# P5 — Gestión SaaS

Casos de uso: **CU28–CU31**.

## Responsabilidad

Gestionar planes, suscripciones, límites de uso y pagos de la plataforma.

## Dependencias previstas

- El adaptador de pagos definido en `app/integrations/payments`.
- P1 para identificar al titular de la suscripción.

## No permitido

- Gestionar documentos, simulaciones o evaluaciones.
- Acoplar reglas de negocio al SDK de un proveedor de pagos.

## Estado

Pendiente. El paquete sólo declara el límite funcional hasta que sus casos de uso sean
implementados.
