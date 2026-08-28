# P1 — Gestión de identidad y seguridad

Casos de uso: **CU01–CU05**.

## Responsabilidad

Gestionar cuentas, credenciales, perfiles, roles y el ciclo de vida de las sesiones. P1 es
propietario de las tablas `users`, `roles`, `user_roles` y `sessions`.

## Capas implementadas

```text
routes -> services -> repositories -> PostgreSQL
   |          |
schemas    models
   |
policies
```

En esta fase, las funciones de FastAPI en `routes/` cumplen también la responsabilidad de
controlador. Se añadirá una capa `controllers/` separada sólo cuando exista orquestación que no
pertenezca al transporte HTTP ni a los servicios de aplicación.

## Dependencias permitidas

- `app/core` para configuración, seguridad y base de datos.
- Ningún proveedor externo específico.

## No permitido

- Gestionar documentos o simulaciones.
- Ejecutar evaluaciones.
- Gestionar pagos o administración de la plataforma.

## Estado

Implementado y cubierto por las pruebas de autenticación y perfil.

El alta aplica una política de contraseña de 15–128 caracteres, acepta espacios sin recortarlos y
rechaza claves comunes, repetitivas, secuenciales o previsibles según el contexto. El login conserva
un mensaje genérico para no revelar si una cuenta existe. La política y su UX están descritas en
[`docs/security/password-policy.md`](../../../../docs/security/password-policy.md).

La protección de login aplica bloqueos progresivos de 5, 10 y 15 minutos por cuenta, una ventana
deslizante por IP y eventos persistentes de seguridad. La decisión está documentada en
[`docs/security/login-protection.md`](../../../../docs/security/login-protection.md).
