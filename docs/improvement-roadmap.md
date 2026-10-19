# Socratia: investigación y mejoras pendientes

Revisión del 18 de octubre de 2026. Las características de terceros se contrastaron
con sus repositorios y publicaciones; no se ejecutaron sus servidores ni se
consideran demostraciones de rendimiento o precisión de Socratia.

## Qué se aplicó

La inferencia de cámara pasó a un Worker con una captura pendiente como máximo;
los recursos públicos tienen caché y los jurados comienzan con vídeo ligero.
La navegación comparte consultas durante diez segundos y anticipa lecturas por
intención; el panel carga sus consultas en paralelo. Las vistas estructurales
reemplazan ruedas de espera, respetando movimiento reducido. Estas vistas no
aceleran por sí mismas la red ni simulan porcentajes de procesamiento.

Fuentes: [Next.js: precarga](https://nextjs.org/docs/app/guides/prefetching),
[web.dev: tareas prolongadas](https://web.dev/articles/optimize-long-tasks),
[web.dev: trabajo fuera del hilo principal](https://web.dev/articles/off-main-thread).

## Proyectos comparables y decisiones

| Referencia primaria | Patrón útil | Decisión para Socratia |
| --- | --- | --- |
| [DeepInterview](https://github.com/ngoanpv/DeepInterview), Apache 2.0 | Separar preparación, conversación y evaluación; preparar el plan antes de hablar | Priorizar preguntas y repreguntas preparadas antes de la sesión. Su README distingue adaptadores simulados de proveedores reales; no es evidencia de una llamada gratuita lista para producción. |
| [MockMate](https://github.com/mockmate-app/mockmate), MIT | Personas del entrevistador y progresión de habilidades | Evaluar un historial de debilidades por rúbrica. No copiar inferencias de confianza o personalidad desde expresiones como si fueran calificaciones objetivas. |
| [Interview Room](https://github.com/dwain-barnes/interview-room), MIT | Conversación de voz y alternativas de avatar | Su ruta local requiere modelos y recursos adicionales; no instalarla en esta laptop. Los servicios externos conservan sus límites y precios. |
| [Virtual Interviewers, Real Results](https://arxiv.org/abs/2506.16542), estudio exploratorio con 20 participantes | Percepción de utilidad junto con problemas de ritmo conversacional | Medir interrupciones y demora entre turnos con estudiantes; no presentar el estudio como validación de nuestras notas automáticas. |

No se copió código de estos proyectos. Antes de incorporar dependencias se debe
revisar mantenimiento, licencia de modelos y datos, consumo y contrato de API.

## Próximas mejoras, con criterios verificables

1. **Trabajos persistentes para documentos e IA.** Implementados en la entrega del
   19 de octubre para procesamiento, preguntas y presentaciones. Hay identificador,
   estados reales, deduplicación y consulta al volver a la página. Una interrupción
   de servidor no repite automáticamente llamadas externas de resultado incierto.
   La evaluación conserva respuestas ya terminadas para reintentos posteriores.
   Falta convertir también la evaluación completa en un trabajo independiente.
2. **Medición por etapa.** Las tareas registran duración y HTTP publica Server-Timing.
   Falta registrar tiempos separados de extracción, recuperación,
   generación y primera voz sin texto privado. Medir p50/p95 con 1, 2 y 5 usuarios
   ficticios antes de ampliar capacidad. No hay todavía una cifra fiable de
   concurrencia soportada ni un porcentaje general de aceleración.
3. **Preparación conversacional.** Preparar preguntas y rúbricas antes de entrar;
   mantener respuestas adaptativas durante la defensa. Criterio: medir tiempo al
   primer audio, repreguntas pertinentes y turnos sin solapamiento con fallos de red.
4. **Detección contrastada con cámara física.** Evaluar ausencia, gafas, iluminación,
   giro de cabeza y encuadres. Mostrar “no verificable” cuando falte torso o iris.
   Vestimenta requiere una evaluación visual aparte; no deducirla de los hombros.
5. **Resultados con evidencia.** Vincular observaciones al turno y fuentes del PDF;
   permitir revisar afirmaciones y comparar prácticas con la misma rúbrica.
6. **Preparación operativa.** Ensayar restauración de respaldo, límites de consumo
   de proveedores, reinicio de sesión y descarga de informes antes de presentación.

## Recursos y costes

La prueba cloud observada generó una presentación en unos 21,6 segundos: las
vistas previas no eliminan esa espera del proveedor. La exportación PPTX ya incluye
texto editable y un anexo de figuras extraídas, sin inventar su correspondencia
con cada diapositiva. No está implementada la ilustración generativa por página.

[Colab](https://research.google.com/colaboratory/faq.html) sirve para experimentos
interactivos sujetos a disponibilidad y condiciones; no se adopta como servidor
permanente. Las API de Gemini, Groq o avatares no consumen automáticamente créditos
AWS. No se habilitó ningún proveedor de pago ni se amplió el servidor por esta
investigación. Más modelos no sustituyen una medición de latencia y exactitud.
