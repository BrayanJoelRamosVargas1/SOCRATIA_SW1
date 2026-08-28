# Protección progresiva de inicio de sesión

P1 combina dos controles persistentes para reducir ataques de fuerza bruta sin depender de la
memoria de una única réplica.

## Bloqueo progresivo por cuenta

| Fallos consecutivos | Bloqueo |
| ---: | ---: |
| 1–2 | Sin bloqueo |
| 3 | 5 minutos |
| 4 | 10 minutos |
| 5 o más | 15 minutos |

Un login correcto reinicia el estado. También se reinicia el escalamiento cuando transcurren 24
horas sin nuevos fallos. Los intentos realizados mientras la cuenta está bloqueada no aumentan el
nivel, evitando que un tercero prolongue el bloqueo sólo por insistir.

La respuesta de una contraseña incorrecta y la de una cuenta temporalmente bloqueada es idéntica;
la API no confirma que una cuenta exista.

## Ventana deslizante por IP

La API admite por defecto 20 intentos por IP durante 60 segundos. Al superar el límite responde
`429` con un mensaje genérico. Los valores se configuran con `LOGIN_IP_MAX_ATTEMPTS` y
`LOGIN_IP_WINDOW_SECONDS`.

Los eventos se guardan en PostgreSQL, por lo que el límite funciona con reinicios y múltiples
réplicas. No se utiliza un contador en memoria.

## Trazabilidad

`authentication_events` registra `LOGIN_FAILED`, `LOGIN_LOCKED`, `LOGIN_REJECTED_LOCKED`,
`LOGIN_RATE_LIMITED` y `LOGIN_SUCCESS`. Los identificadores de cuentas inexistentes se guardan como
HMAC-SHA256, nunca como correo en texto claro. P6 podrá consultar esta trazabilidad mediante una
interfaz explícita en un incremento posterior.

## Consideraciones operativas

- La recuperación de contraseña permanece disponible durante un bloqueo.
- CAPTCHA queda como defensa adicional posterior.
- `X-Forwarded-For` se ignora por defecto. En producción, el proxy debe reemplazar ese header y se
  habilita su lectura con `TRUST_PROXY_HEADERS=true`; nunca debe activarse detrás de un proxy que
  reenvíe valores proporcionados libremente por el cliente.

Referencia: [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html).
