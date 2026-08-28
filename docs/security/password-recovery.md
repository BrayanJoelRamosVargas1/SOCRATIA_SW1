# Recuperación de contraseña y SMTP

## Flujo

1. `POST /api/v1/auth/forgot-password` siempre devuelve el mismo mensaje y código, exista o no la
   cuenta.
2. Para una cuenta activa se genera un token aleatorio de 32 bytes. PostgreSQL almacena únicamente
   su SHA-256, nunca el valor que viaja por correo.
3. El enlace se construye desde `FRONTEND_URL`, no desde la cabecera `Host` de la solicitud. Vence
   en 15 minutos y una nueva solicitud invalida todos los enlaces anteriores.
4. `POST /api/v1/auth/reset-password` valida el token y la misma política de contraseñas del alta.
5. Al completar el cambio, el token queda usado, se reinicia cualquier bloqueo y se revocan refresh
   sessions y access tokens mediante `users.auth_version`.

Las solicitudes se limitan por identificador anonimizado y por IP en una ventana persistente de una
hora. Los eventos `PASSWORD_RESET_REQUESTED` y `PASSWORD_RESET_COMPLETED` quedan disponibles para
la auditoría de P6 sin registrar direcciones de correo ni tokens.
Si la aplicación está detrás de un proxy controlado, `TRUST_PROXY_HEADERS=true` permite aplicar el
límite a la IP original; no debe activarse cuando el cliente pueda alcanzar FastAPI directamente.

## Brevo SMTP real

El runtime usa `SmtpEmailProvider`; no contiene un modo simulado. Las pruebas sustituyen la interfaz
por `FakeEmailProvider` para no contactar servicios externos.

Antes de iniciar el backend, crea `.env` desde `.env.example` y completa:

```dotenv
FRONTEND_URL=https://tu-dominio.example
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USERNAME=tu-login@smtp-brevo.com
SMTP_PASSWORD=una-clave-smtp-nueva
SMTP_STARTTLS=true
SMTP_USE_SSL=false
MAIL_FROM_NAME=Socratia
MAIL_FROM_EMAIL=remitente-verificado@tu-dominio.example
```

`MAIL_FROM_EMAIL` debe ser un remitente o dominio validado en Brevo. Se utiliza una **clave SMTP**,
no una API key. Ningún secreto debe entrar a Git; `.env` está ignorado por el repositorio. Si una
clave fue pegada en un chat, issue o log, debe revocarse y reemplazarse antes de utilizar el flujo.

El envío se realiza como tarea posterior a la respuesta para reducir enumeración por tiempo. Un
fallo del relay se registra sin correo ni token y la respuesta pública continúa siendo genérica.

## Variables ajustables

- `PASSWORD_RESET_TOKEN_TTL_MINUTES=15`
- `PASSWORD_RESET_MAX_REQUESTS_PER_IDENTIFIER=3`
- `PASSWORD_RESET_MAX_REQUESTS_PER_IP=10`
- `PASSWORD_RESET_RATE_WINDOW_SECONDS=3600`
- `SMTP_TIMEOUT_SECONDS=15`

En producción también deben configurarse HTTPS, `COOKIE_SECURE=true`, un `JWT_SECRET` aleatorio y
`FRONTEND_URL` con el origen público exacto.
