# Guía y chatbot de Socratia

Son dos funciones distintas en la web autenticada, disponibles para estudiantes y administradores:

- **Guía de uso**: procedimientos y destinos verificados del producto. Conserva `POST /api/v1/help/ask` y su opción de explicación adicional.
- **Chatbot**: conversación general, con enfoque académico, mediante `POST /api/v1/help/chat`. Mantiene un historial temporal de hasta ocho mensajes enviados al servidor. No consulta documentos automáticamente ni realiza acciones sobre los datos.

## Proveedores y privacidad

El chat comienza en **IA propia** (`local_only=true`). Requiere un modelo conversacional compatible con Chat Completions, configurado mediante `SELF_HOSTED_LLM_URL`, `SELF_HOSTED_LLM_KEY_FILE` (o la clave privada `SELF_HOSTED_LLM_KEY`) y `SELF_HOSTED_LLM_MODEL`. La clave solo debe configurarse en el servidor. El modelo Qwen de embeddings no es compatible con conversación y su dirección no debe reutilizarse como servidor de chat.

Si falta el modelo, se informa sin simular una respuesta neuronal ni llamar a Groq. La opción **IA disponible** permite usar el proveedor externo configurado cuando no hay modelo propio. No se cambia automáticamente a un proveedor externo cuando falla el modelo propio.

Las respuestas identifican el motor real. El historial permanece en la memoria de la pestaña, se limita a ocho mensajes de hasta 1200 caracteres y se borra al recargar o pulsar Nuevo chat. La consulta admite hasta 600 caracteres. Al usar IA externa se envían la consulta y ese historial al proveedor. No introducir credenciales ni datos privados en los mensajes.

El límite compartido con la ayuda es de cinco solicitudes de IA por usuario cada cinco minutos en el proceso actual; una ausencia de configuración local no consume ese cupo. No es un límite monetario distribuido. La inferencia propia del chat tiene un timeout de lectura de 45 segundos y la externa de 12; no hay reintentos automáticos. La guía mantiene 20 segundos para su explicación opcional. Una respuesta incompleta se presenta como fallo, sin inventar una contestación de reemplazo.

## Validación y estado de entrega

- Desde `backend`, ejecutar `.venv/Scripts/python.exe -m pytest tests/test_product_chat.py -q`: contrato HTTP, autenticación, límites de historial, permisos, separación de guía/chatbot y proveedores simulados.
- En frontend: `npm run test:chat`, TypeScript y ESLint de los archivos modificados.
- La vista de `artifacts/chat-preview` utiliza el componente real con API simulada; no es evidencia de inferencia en AWS.

La incorporación inicial es web. La APK conserva su ayuda existente; no se ha compilado una APK con una pantalla de chatbot. La publicación se realiza desde main tras autorización; los archivos GGUF presentes en disco no prueban por sí solos que el servicio esté arrancado.

## Servicio conversacional en AWS

`compose.chat.yaml` usa la red privada existente del piloto y no publica puertos. Qwen3-0.6B-Q8_0 se ejecuta en CPU con contexto 4096, un turno a la vez y memoria limitada. No crea una GPU ni otra instancia. Los pesos y la clave se montan en solo lectura. Se reutiliza la clave privada interna existente sin copiarla a Git ni al navegador.

Antes de iniciar, verificar `/opt/socratia-qwen/models/Qwen3-0.6B-Q8_0.gguf`: 639446688 bytes, SHA-256 `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`, coincidente con el archivo del repositorio oficial Qwen. El despliegue no descarga modelos automáticamente.

Desde `/opt/socratia` ejecutar `docker compose -f compose.chat.yaml up -d`. La configuración privada del backend usa `SELF_HOSTED_LLM_URL=http://socratia-chat:8080/v1`, `SELF_HOSTED_LLM_KEY_FILE=/run/socratia-secrets/qwen-api-key` y `SELF_HOSTED_LLM_MODEL=Qwen3-0.6B-Q8_0`. Hay que recrear el backend después de actualizar esa configuración. Mantener los generadores de materiales con su proveedor actual: activar el chat no debe cambiar `PREPARATION_PRIMARY_PROVIDER`.

Comprobar salud, petición autenticada a /help/chat, respuesta en español con engine=modelo_propio y tiempos/memoria. Para apagar solo la conversación, `docker compose -f compose.chat.yaml stop chat`; no eliminar los volúmenes del piloto. El modelo pequeño puede equivocarse y no sustituye fuentes verificadas.
