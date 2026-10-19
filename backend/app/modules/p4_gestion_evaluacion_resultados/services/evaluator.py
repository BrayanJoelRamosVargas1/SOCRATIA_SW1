from groq import AsyncGroq

from app.core.config import get_settings
from app.modules.p4_gestion_evaluacion_resultados.schemas.evaluation import TurnEvaluationResult

settings = get_settings()

EVALUATION_SYSTEM_PROMPT = """Eres el Evaluador Académico Principal de la plataforma Socratia para defensas formales de grado y posgrado.
Tu tarea es evaluar con rigor técnico, objetividad epistemológica y precisión quirúrgica cada intervención del postulante frente a:
1. La pregunta formulada por el jurado examinador.
2. El contexto autorizado extraído exclusivamente de la tesis/documento de investigación.
3. Si es una repregunta (follow-up), el contexto de la pregunta padre y los puntos clave esperados.

CRITERIOS ESTRICTOS DE CLASIFICACIÓN Y CALIFICACIÓN:
- PRECISE (Puntaje 80-100): El postulante responde con exactitud técnica y conceptual, cita la metodología/algoritmo correcto y demuestra dominio temático solvente.
- INCOMPLETE (Puntaje 25-75): El postulante responde de forma superficial, parcial o evade detalles cruciales de la pregunta.
- CONTRADICTORY (Puntaje 0-20): El postulante contradice los postulados de su tesis, emite afirmaciones falsas, responde con una evasiva como 'no sé / no lo sabría decir' o muestra confusión conceptual severa.

DIRECTRICES OBLIGATORIAS:
- Redacta fortalezas (strengths), debilidades (weaknesses), puntos faltantes (missing_points) y contradicciones (contradictions) en español formal y técnico.
- Extrae citas textuales verificables de la respuesta del postulante en el array 'evidence'.
- Si la respuesta carece de contenido técnico ('no sé', preguntas retóricas, silencios), asigna un puntaje de 0 a 10 e identifica detalladamente en 'missing_points' los conceptos exactos del documento que debió haber expuesto.
- No evalúes basándote en suposiciones externas: juzga únicamente la consistencia contra el contexto autorizado y los puntos esperados.
"""


class Evaluator:
    def __init__(
        self,
        provider: str = "groq",
        model: str | None = None,
        temperature: float = 0.0,
    ):
        self.provider = provider
        self.temperature = temperature
        if provider == "groq":
            import instructor

            self.model = model or settings.groq_question_model
            api_key = settings.groq_api_key.get_secret_value() if settings.groq_api_key else ""
            raw_client = AsyncGroq(api_key=api_key, max_retries=0, timeout=45)
            self.client = instructor.from_groq(raw_client, mode=instructor.Mode.TOOLS)
            self._init_error = None
        else:
            self.model = model or settings.gemini_question_model
            try:
                from google import genai
                from instructor.v2.providers.genai.client import from_genai

                api_key = (
                    settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else ""
                )
                raw_client = genai.Client(api_key=api_key)
                self.client = from_genai(raw_client)
                self._init_error = None
            except (ImportError, ModuleNotFoundError) as err:
                self.client = None
                self._init_error = str(err)

    async def evaluate_turn(
        self,
        question: str,
        student_response: str,
        context_text: str,
        expected_points: list[str] | None = None,
    ) -> TurnEvaluationResult:
        if self.client is None:
            raise RuntimeError(
                f"Evaluator provider '{self.provider}' is not available: "
                f"{getattr(self, '_init_error', 'client was not initialized')}"
            )

        prompt = f"Question: {question}\n\n"
        if expected_points:
            prompt += (
                "Expected Points (from parent if follow-up):\n- "
                + "\n- ".join(expected_points)
                + "\n\n"
            )

        prompt += f"Authorized Context (DO NOT use external knowledge):\n{context_text}\n\n"
        prompt += f"Student Response:\n{student_response}\n\n"
        prompt += "Evaluate the student response strictly based on the provided context."

        import inspect

        if inspect.iscoroutinefunction(self.client.chat.completions.create):
            response = await self.client.chat.completions.create(
                model=self.model,
                response_model=TurnEvaluationResult,
                messages=[
                    {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_retries=settings.evaluation_max_retries,
                max_tokens=2048,
                temperature=self.temperature,
            )
        else:
            import anyio

            def sync_create():
                return self.client.chat.completions.create(
                    model=self.model,
                    response_model=TurnEvaluationResult,
                    max_retries=settings.evaluation_max_retries,
                    messages=[
                        {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.temperature,
                )

            response = await anyio.to_thread.run_sync(sync_create)

        return response
