from app.integrations.llm.jury_base import JuryRoutingRequest

SYSTEM_PROMPT = """You are an expert academic jury member evaluating a student's answer.
Your task is to analyze the student's answer against the original question and the expected answer points.
You must return a JSON object containing your decision on whether to ask a follow-up question or proceed to the next bank question.
If the student's answer is incomplete, incorrect, or requires further clarification based on your strictness and interruption level, you should output "FOLLOW_UP" and provide a follow_up_question.
Otherwise, output "NEXT_BANK".
"""


def build_jury_prompt(request: JuryRoutingRequest) -> str:
    points_text = "\n".join(f"- {p}" for p in request.expected_answer_points)
    return f"""
EVALUATION CONTEXT:
Question: {request.question_text}
Expected Answer Points:
{points_text}

JURY PROFILE:
Focus Type: {request.focus_type}
Strictness (1-5): {request.strictness}
Interruption Level: {request.interruption_level}

STUDENT ANSWER:
{request.student_answer}
"""
