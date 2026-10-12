from groq import AsyncGroq

from app.core.config import get_settings
from app.modules.p4_gestion_evaluacion_resultados.schemas.evaluation import TurnEvaluationResult

settings = get_settings()

EVALUATION_SYSTEM_PROMPT = """You are an expert AI evaluator for professional interview simulations.
Your task is to evaluate a single response (turn) from a student based on:
1. The question asked.
2. The provided reference context from the primary document.
3. If it's a follow-up question, the context of the parent question.

Guidelines:
- Classify the response as PRECISE, INCOMPLETE, or CONTRADICTORY.
- Do NOT infer expected answer points for follow-up questions freely. Use the parent question's expected points and the authorized context. If no evidence is found in the context, evaluate strictly based ONLY on the provided context.
- Assign a score from 0 to 100.
- Provide lists of strengths, weaknesses, missing points, and contradictions.
- Extract concrete evidence (quotes) from the transcription to back up your claims.
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
            raw_client = AsyncGroq(api_key=api_key)
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
                max_tokens=2048,
                temperature=self.temperature,
            )
        else:
            import anyio

            def sync_create():
                return self.client.chat.completions.create(
                    model=self.model,
                    response_model=TurnEvaluationResult,
                    messages=[
                        {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.temperature,
                )

            response = await anyio.to_thread.run_sync(sync_create)

        return response
