# Revisión de idioma y repreguntas — 6 de noviembre de 2026

La revisión detectó un banco de demostración con doce preguntas antiguas en inglés. La migración `20261106_0014` aplica traducciones revisadas de esas preguntas tanto al banco como a las preguntas y turnos del jurado ya almacenados. Conserva los identificadores, las respuestas de estudiantes, los documentos originales y las calificaciones. Guarda los valores anteriores para permitir una reversión condicional.

Las nuevas preguntas, repreguntas, diapositivas y observaciones de evaluación pasan por una comprobación local de idioma. No descarga modelos ni utiliza una API de traducción. El detector es una protección adicional, no una garantía de identificación perfecta; admite nombres propios, siglas y fragmentos técnicos breves. Las citas de respuestas del estudiante se conservan literalmente.

Se tradujeron mensajes de autenticación, administración, suscripciones y validación; se ajustaron etiquetas visibles y formatos regionales. Los identificadores de protocolos y roles internos conservan su contrato original.

`GET /api/v1/admin/language-audit` permite revisar por páginas los grupos `questions`, `jury_turns`, `presentations`, `slides` y `feedback`. Requiere administrador y devuelve únicamente cantidades e identificadores, nunca el texto privado. No llama a proveedores de IA.

La inserción de repreguntas ahora desplaza las posiciones en orden descendente para respetar su restricción de unicidad. Verifica que la pregunta padre pertenezca a la misma simulación y actualiza el total de preguntas. El reporte incluye las repreguntas respondidas.

Validación: suite específica `python infrastructure/scripts/run_defense_tests.py --suite spanish`; suite general `--suite release`; comprobación de TypeScript y pruebas de cliente API, caché y subida. Se ejecutan con proveedores simulados y PostgreSQL temporal. Los resultados locales y la evidencia de producción se guardan en `artifacts/defense-validation`, excluido de Git.
