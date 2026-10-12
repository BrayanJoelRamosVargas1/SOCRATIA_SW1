import instructor
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
            self.model = model or settings.groq_question_model
            api_key = settings.groq_api_key.get_secret_value() if settings.groq_api_key else ""
            client = AsyncGroq(api_key=api_key)
            self.client = instructor.from_groq(client, mode=instructor.Mode.TOOLS)
        else:
            import google.generativeai as genai

            api_key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else ""
            genai.configure(api_key=api_key)
            client = genai.GenerativeModel(model or settings.gemini_question_model)
            self.client = instructor.from_gemini(client, mode=instructor.Mode.GEMINI_JSON)
            self.model = model or settings.gemini_question_model

    async def evaluate_turn(
        self,
        question: str,
        student_response: str,
        context_text: str,
        expected_points: list[str] | None = None,
    ) -> TurnEvaluationResult:

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

        if self.provider == "groq":
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
            response = await self.client.chat.completions.create(
                response_model=TurnEvaluationResult,
                messages=[
                    {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                generation_config={"temperature": self.temperature},
            )

        return response
