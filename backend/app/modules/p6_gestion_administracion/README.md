# P6 — Gestión de administración

Casos de uso: **CU32–CU37**.

## Responsabilidad

Administrar la plataforma, supervisar su operación y mantener la trazabilidad de acciones
relevantes.

## Dependencias previstas

- Servicios administrativos expuestos explícitamente por P1–P5.
- Infraestructura de observabilidad y persistencia de auditoría.
- Eventos normalizados de proveedores: capacidad, proveedor, latencia, resultado, fallback y
  estado del circuito.

## No permitido

- Acceder de forma accidental a repositorios internos de otros paquetes.
- Duplicar las reglas de negocio de P1–P5.

## Estado

Pendiente. El paquete sólo declara el límite funcional hasta que sus casos de uso sean
implementados.

P6 será consumidor de la telemetría de integraciones, no propietario de sus routers. Sus paneles
podrán mostrar disponibilidad, latencia y fallbacks sin almacenar credenciales, tokens, prompts ni
documentos. Véase [`docs/provider-resilience.md`](../../../../docs/provider-resilience.md).
