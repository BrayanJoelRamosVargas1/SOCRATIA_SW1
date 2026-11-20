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

## Cierre de comprobación en AWS

- Versión de ejecución 2260c93 publicada y verificada en RELEASE.json. Interfaz visible: límite 50 MB, Probar aviso y pasos de Android/iPhone; sin suscripción devuelve «Primero activa los avisos en este dispositivo», sin afirmar entrega.
- Recorrido real sobre el PDF ficticio de 21 MiB: preguntas SUCCEEDED en 21.317 ms (Gemini alternativo); presentación SUCCEEDED en 26.857 ms. Se descargaron y validaron las 12 preguntas españolas en PDF y 10 diapositivas PPTX. Los tiempos no son una garantía para documentos grandes reales.
- Modelo Kokoro ONNX ejecutado en contenedor aislado con --network none, CPU 0,75 y RAM 600 MiB, usando los modelos ya instalados: produjo WAV válido de 127.562 bytes en 12,43 s. No hubo descarga ni inferencia en la laptop. Esto demuestra síntesis de voz neuronal autohospedada sin API externa; no demuestra Qwen conectado al flujo de producción.
- Sigue pendiente la recepción física de Web Push en Android/iPhone y la conexión segura de Qwen al flujo. Kaggle quedó con GPU detenida. La documentación académica permanece fuera de alcance.

## Hoja del docente: transcripción de los requisitos de software

1. La app está completamente y correctamente terminada en un 100 %, de acuerdo a lo descrito en la definición de dicho proyecto.
2. La aplicación implementa funcionalidades basadas en IA en modo local que vayan más allá de un chat, reconocimiento de imagen.
3. La app contiene funcionalidades para ser publicadas en versión móvil que incluya notificaciones tipo push.
4. La app está diseñada y desplegada en infraestructura como AWS, Azure, Google Cloud, y cuenta con un asistente inteligente para guiar al usuario para aprender a usar la app correctamente.
5. Documentación: excluida por pedido del equipo; el borde de la foto además recorta parte del texto.

### Nueva tanda de fallas reportadas

- Selector de simulación vacío: la interfaz ocultaba documentos sin preguntas listas y también ocultaba errores de consulta. Ahora lista todos los archivos, identifica si falta procesamiento o preguntas y enlaza a la preparación; solo habilita continuar con banco comprobado.
- Doble clic en generación: bloqueo inmediato con referencia, además del estado visual y la exclusión de tareas en servidor. No es necesario insistir mientras una tarea esté en curso.
- Contraste: texto claro, controles y mensajes legibles en la tarjeta oscura de calibración y vestimenta.
- PPTX: reemplazar la lista uniforme por tarjetas numeradas editables en una o dos columnas, jerarquía de texto y tiempo de exposición; conservar texto completo en notas y figuras atribuidas. Este cambio no equivale a diseño de una API externa ni certifica aún calidad visual renderizada.
- Propuesta móvil: PWA instalable para Android/iPhone con carga, historial, práctica por texto/audio y avisos. Si el docente exige APK, evaluar cliente Capacitor con pantallas móviles y autenticación contra la API, evitando una mera promesa de publicar la web. iOS requiere herramientas/firma de Apple; no se ha generado APK/IPA.
- API de presentaciones investigada: Gamma permite generación/exportación PPTX, pero su API consume créditos y requiere acceso de plan correspondiente. No se activó gasto ni se enviaron documentos privados. Fuentes: https://developers.gamma.app/ y https://gamma.app/pricing . Capacitor: https://capacitorjs.com/docs .

- La consulta real de límites devolvió 8.000 tokens/minuto para el modelo Groq configurado. Se reduce el contexto alternativo por defecto a 5.000 caracteres, manteniendo selección por fuentes y la validación; no es una promesa de cuota ilimitada.
- Se reprodujo un rechazo de banco por más de seis puntos internos de respuesta en una pregunta. El lector de respuesta acota únicamente ese campo interno a seis elementos; siguen obligatorios exactamente doce preguntas, categorías, español e identificadores de fuentes autorizadas. Prueba de regresión conserva rechazo de una fuente ajena.
- Alternativa de presentaciones investigada: Presenton, API de código abierto con exportación PPTX/PDF. No se instala en el piloto pequeño sin medir recursos ni se asume que sus proveedores de IA sean gratis: https://github.com/presenton/presenton .

- Si Groq devuelve `json_validate_failed` con `failed_generation`, la salida se somete a nuestras mismas validaciones completas antes de aceptarla. No se acepta el texto del error como resultado sin comprobarlo ni se eliminan controles de fuentes; prueba de regresión rechaza una fuente ajena incluso en esta ruta.
