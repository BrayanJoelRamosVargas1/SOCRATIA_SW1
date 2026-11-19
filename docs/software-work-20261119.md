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
