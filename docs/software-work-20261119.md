# Trabajo de software solicitado — 19/11/2026

| ID | Pedido | Criterio de aceptación |
|---|---|---|
| S01 | Archivos grandes | PDF/DOCX hasta 50 MiB, mismo límite en interfaz/API/AWS, comprobar archivo real >20 MiB; conservar validación y procesamiento acotado. |
| S02 | Banco de preguntas PDF | Descarga autenticada, propietario verificado, español legible, paginación; nunca exportar respuestas esperadas internas. |
| S03 | Rapidez de preparación | Reutilizar resultados existentes, proveedor alternativo acotado, tareas persistentes, medir generación real sin prometer segundos constantes. |
| S04 | Push móvil real | Suscripción voluntaria, Web Push VAPID desde servidor al finalizar/fallar tarea, revocación, sin texto privado del documento, PWA instalable. |
| S05 | Asistente de uso | Ayuda contextual sobre pasos reales del producto, español, sin instrucciones inventadas ni acceso entre usuarios. |
| S06 | IA propia GPU | Adaptador autenticado y con timeout para modelo autohospedado; notebook reproducible Qwen GPU remota; no inferencia pesada en laptop/EC2 t3.small. Demostración real requiere sesión GPU disponible. |
| S07 | Criterios del docente | Demostrar IA más allá del chat: preparación RAG/evaluación/visión/voz, móvil/push, AWS/asistente; documentación académica fuera de este trabajo. |

Kaggle ofrece sesiones y cuotas, no se asumirá disponibilidad permanente. Un modelo propio en Kaggle es inferencia autohospedada remota, no local a la laptop. No se crearán recursos de pago ni se publicarán endpoints sin autenticación.

## Verificación y pendientes concretos

- AWS publica 50 MiB y aceptó un PDF sintético de 22.038.806 bytes. El texto se procesó en 1.638 ms. La transferencia desde la conexión del equipo tomó 302,88 s: esto no demuestra rapidez de subida ni representa una tesis compleja de muchas páginas.
- La descarga real del banco existente devolvió PDF legible con las 12 preguntas; se comprobó autorización del propietario en pruebas de integración.
- Push VAPID configurado en AWS. Se añadió una prueba voluntaria limitada a un envío por minuto por usuario y proceso. La aceptación del proveedor no demuestra recepción: debe verificarse en un dispositivo con permisos concedidos.
- Se corrigieron textos con codificación dañada en los componentes de ayuda y avisos.
- Una prueba real detectó que la búsqueda vectorial directa en PostgreSQL descartaba resultados al intentar acceder a `.primary`. Corregido para conservar el resultado semántico y su modo de recuperación; hay prueba de regresión.
- Qwen3-4B-Instruct-2507 generó una pregunta crítica en español en una Tesla T4 de Kaggle en 13,61 s. Notebook privado guardado y GPU detenida. El adaptador del sistema existe; esa sesión no es un endpoint conectado ni permanente.
- Kokoro es el modelo neural de síntesis de voz autohospedado del sistema; no confundirlo con voces del navegador ni declarar E5/Qwen activos sin verificar su configuración y ejecución.
- La generación nueva de preguntas falló en una prueba sobre el documento sintético; sigue pendiente revalidar causa y medir diapositivas. No se declara el software 100 % terminado ni una nota académica garantizada.

- Comparación interna: la API dentro de AWS recibió el mismo PDF de 21 MiB en 2,73 s. Esta medición excluye Internet y el proxy público; permite distinguir guardado de transferencia, sin atribuir aún toda la demora a un único tramo.
- Una generación diagnóstica de Groq sobre el mismo contexto ficticio fue válida en 2,74 s. Un fallo aislado de formato puede ocurrir; preguntas y diapositivas ahora permiten una sola corrección tras una respuesta inválida conocida. Se conserva validación estricta y, con un intento configurado, pueden consumirse hasta dos completaciones por proveedor Groq; esta corrección no repite fallos de red/autenticación.
- Instrucciones visibles para Android y para iOS/iPadOS 16.4+ como aplicación añadida a inicio, según WebKit: https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/ . La recepción física en ambos sistemas sigue sin certificarse.
- Segunda tanda: 35 pruebas de móvil/preparación/apagado pasaron; TypeScript y ESLint de los componentes modificados pasaron, sin compilar producción ni cargar modelos en la laptop.
