# Guía y chatbot de Socratia

Son dos funciones distintas en la web autenticada, disponibles para estudiantes y administradores:

- **Guía de uso**: procedimientos y destinos verificados del producto. Conserva `POST /api/v1/help/ask` y su opción de explicación adicional.
- **Chatbot**: conversación general, con enfoque académico, mediante `POST /api/v1/help/chat`. Mantiene un historial temporal de hasta ocho mensajes enviados al servidor. No consulta documentos automáticamente ni realiza acciones sobre los datos.

## Proveedores y privacidad

El chat comienza en **IA propia** (`local_only=true`). Requiere un modelo conversacional compatible con Chat Completions, configurado mediante `SELF_HOSTED_LLM_URL`, `SELF_HOSTED_LLM_KEY` y `SELF_HOSTED_LLM_MODEL`. La clave solo debe configurarse en el servidor. El modelo Qwen de embeddings no es compatible con conversación y su dirección no debe reutilizarse como servidor de chat.

Si falta el modelo, se informa sin simular una respuesta neuronal ni llamar a Groq. La opción **IA disponible** permite usar el proveedor externo configurado cuando no hay modelo propio. No se cambia automáticamente a un proveedor externo cuando falla el modelo propio.

Las respuestas identifican el motor real. El historial permanece en la memoria de la pestaña, se limita a ocho mensajes de hasta 1200 caracteres y se borra al recargar o pulsar Nuevo chat. La consulta admite hasta 600 caracteres. Al usar IA externa se envían la consulta y ese historial al proveedor. No introducir credenciales ni datos privados en los mensajes.

El límite compartido con la ayuda es de cinco solicitudes de IA por usuario cada cinco minutos en el proceso actual; una ausencia de configuración local no consume ese cupo. No es un límite monetario distribuido. La inferencia propia tiene un timeout de lectura de 20 segundos y la externa de 12; no hay reintentos automáticos. Una respuesta incompleta se presenta como fallo, sin inventar una contestación de reemplazo.

## Validación y estado de entrega

- Desde `backend`, ejecutar `.venv/Scripts/python.exe -m pytest tests/test_product_chat.py -q`: contrato HTTP, autenticación, límites de historial, permisos, separación de guía/chatbot y proveedores simulados.
- En frontend: `npm run test:chat`, TypeScript y ESLint de los archivos modificados.
- La vista de `artifacts/chat-preview` utiliza el componente real con API simulada; no es evidencia de inferencia en AWS.

La incorporación inicial es web. La APK conserva su ayuda existente; no se ha compilado una APK con una pantalla de chatbot. Estos cambios permanecen en la rama de corrección local, sin publicación automática en GitHub, main ni AWS. Para activar el chat propio en AWS hacen falta un modelo conversacional activo, pruebas de memoria/latencia en el servidor de 2 GB y un despliegue autorizado; los archivos GGUF presentes en disco no prueban que ese servicio esté arrancado.
