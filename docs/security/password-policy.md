# Política de contraseñas y UX de autenticación

Estado: implementada como hardening de P1.

## Regla definitiva del backend

FastAPI es la autoridad. El frontend sólo ofrece feedback anticipado.

- Longitud mínima: 15 caracteres porque Socratia usa la contraseña como factor único.
- Longitud máxima: 128 caracteres; supera el mínimo de 64 recomendado para aceptación.
- Sin reglas obligatorias de mayúsculas, números o símbolos.
- Se aceptan frases, Unicode y espacios.
- Los espacios internos, iniciales y finales se conservan exactamente; nunca se aplica `strip()` o
  `trim()` a la contraseña.
- Las nuevas contraseñas se comparan como valor completo con una blocklist compacta de claves
  comunes, patrones repetitivos, secuencias y valores previsibles relacionados con Socratia o la
  identidad declarada.
- Las contraseñas se almacenan con Argon2; nunca en texto plano.
- El login mantiene el mismo mensaje para cuenta inexistente y contraseña incorrecta.

## Comportamiento del frontend

- Botón accesible para mostrar u ocultar cada contraseña.
- `autocomplete="new-password"` en registro y `autocomplete="current-password"` en login.
- Pegado y autocompletado permitidos para gestores de contraseñas.
- Confirmación local que nunca se envía al backend.
- Advertencia cuando Bloq Mayús está activo.
- Advertencia, sin modificación automática, cuando la contraseña empieza o termina con un espacio:

```text
Registro:
Tu contraseña comienza o termina con un espacio. Verifica que sea intencional:
ese espacio se guardará como parte de la contraseña.

Inicio de sesión:
La contraseña comienza o termina con un espacio. Asegúrate de escribirla
exactamente como la registraste.
```

- Medidor de fortaleza orientativo. La validación definitiva siempre ocurre en FastAPI.

## Controles pendientes antes de producción

Este incremento no finge resolver controles que necesitan infraestructura o flujos completos:

- Rate limiting compartido por cuenta e IP; no un contador en memoria que falle con varias réplicas.
- Consulta de un corpus amplio de contraseñas comprometidas mediante un proveedor/adaptador
  confiable.
- Recuperación de contraseña con token de un solo uso, expiración y almacenamiento mediante hash.
- Cambio de contraseña verificando la contraseña actual y revocando sesiones anteriores.
- Visualización y revocación de sesiones activas.
- Verificación de correo y políticas legales publicadas antes de exigir aceptación.

## Referencias

- [NIST SP 800-63B-4 — Passwords](https://pages.nist.gov/800-63-4/sp800-63b.html#passwords)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
