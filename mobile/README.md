# Socratia para Android

Cliente complementario con pantallas empaquetadas en la APK. No carga la web completa ni sus avatares/modelos. Permite iniciar sesión, consultar los documentos propios, leer preguntas y diapositivas ya preparadas, guardar/compartir PDF y PPTX y consultar evaluaciones. No incluye crear simulaciones, cámara, micrófono, generación ni administración. Las autorizaciones del servidor siguen siendo las mismas; ocultar funciones en este cliente no reemplaza el control de acceso de la API.

## Compilación sin exigir a la laptop

El flujo `.github/workflows/mobile-apk.yml` compila en GitHub Actions al cambiar `mobile/` en main o al ejecutarlo manualmente. El artefacto contiene una APK **debug de pruebas**, su SHA256 y certificado de firma y caduca a los 14 días. Desde la versión 0.2.0 conserva una clave del piloto mediante el secreto `ANDROID_PILOT_KEYSTORE_B64`; no es una publicación en Play Store. La transición desde 0.1.0 puede requerir desinstalar la anterior por el cambio de firma. No sobrescribir ese secreto al compilar futuras actualizaciones. La instalación y funcionamiento nativos deben probarse en un Android real (Android 7 o posterior).

El proyecto usa Capacitor 8, Node 22, Java 21 y SDK 36. Para cambios ligeros: `npm ci`, `npm test`, `npm run build`, `npx cap sync android`. No hace falta abrir Android Studio ni compilar Gradle en el equipo del usuario.

## Servidor y privacidad

La dirección del piloto está fijada en `src/policy.mjs`, actualmente `https://socratia.54.221.46.202.sslip.io`. Si cambia la IP del servidor hay que actualizar y recompilar. No se pide al usuario que envíe credenciales a direcciones arbitrarias. Solo HTTPS; cookies de sesión manejadas por HTTP nativo y rotadas por `/auth/refresh`; no se escriben contraseñas o JWT en localStorage. El respaldo Android de los datos de la aplicación está desactivado. Los archivos que se comparten se guardan temporalmente en la caché privada; las copias guardadas voluntariamente fuera de la app permanecen en destino.

## Push nativo (recepción confirmada por el usuario en Android)

Web Push/VAPID no se reutiliza en Android WebView. El cliente usa Firebase Cloud Messaging y pide permiso de notificación voluntariamente. Se desactivó el inicio automático de FCM; la activación requiere acción del usuario.

1. Registrar una app Android `bo.socratia.mobile` en el proyecto Firebase del equipo. No exige habilitar facturación para FCM.
2. Guardar el contenido de `google-services.json` como secreto de GitHub Actions `FIREBASE_ANDROID_JSON`. Es configuración del cliente; **no es la clave privada del servidor**. Nunca introducir una cuenta de servicio en este secreto o en la APK.
3. Montar la cuenta de servicio autorizada para FCM, en modo solo lectura, tanto en backend como en preparation-worker. Configurar `FCM_SERVICE_ACCOUNT_FILE` con la ruta interna. Nunca guardar la clave privada en Git. No activar el indicador hasta que la cuenta sea válida.
4. Recompilar, instalar, iniciar sesión y pulsar Activar notificaciones, luego Probar aviso. Verificar recepción con la app en segundo plano y abrir el documento correcto al tocar el aviso. Verificar también el cierre de sesión y cambio de cuenta.

Sin configuración, los documentos y resultados funcionan y los controles explican que Firebase está pendiente. El servidor almacena como máximo cinco tokens por usuario; los avisos son genéricos, con destino a recursos del propio usuario. Eliminar una suscripción ajena está prohibido. Tokens `UNREGISTERED` se limpian; errores transitorios conservan la suscripción.

Una APK es para Android. iPhone utiliza por ahora la PWA existente; una app nativa iOS requiere un proyecto iOS, macOS y firma de Apple. No se ha generado IPA ni verificado recepción física en iPhone. El usuario confirmó recepción en Android fuera de la pantalla de Socratia; no confirmó si el proceso estaba en segundo plano o cerrado.

Estado del piloto: proyecto `socratia-movil` en Spark, app `bo.socratia.mobile`, configuración de cliente guardada en Actions y cuenta dedicada de servidor montada fuera de Git. AWS validó OAuth y un envío FCM `validate_only` con HTTP 200, sin entrega real. La APK está disponible como prepublicación de pruebas en https://github.com/BrayanJoelRamosVargas1/SOCRATIA_SW1/releases/tag/android-piloto-20261119 .

Fuentes: https://capacitorjs.com/docs/apis/push-notifications y https://firebase.google.com/docs/cloud-messaging/android/client .
