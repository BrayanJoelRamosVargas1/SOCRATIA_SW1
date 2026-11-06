"""Bounded, read-only audit of generated text. Never returns private prose."""
from sqlalchemy import select
from app.core.spanish import foreign_prose
from app.modules.p2_gestion_documentos_preparacion.models.question_bank import Question
from app.modules.p2_gestion_documentos_preparacion.models.presentation_material import PresentationMaterial, PresentationSlide
from app.modules.p3_gestion_simulacion.models import SimulationTurn
from app.modules.p4_gestion_evaluacion_resultados.models.evaluation import TurnEvaluation

GROUPS = {
    "questions": (Question, ["question"]),
    "jury_turns": (SimulationTurn, ["content"]),
    "presentations": (PresentationMaterial, ["title"]),
    "slides": (PresentationSlide, ["title", "objective", "bullet_points", "speaker_notes"]),
    "feedback": (TurnEvaluation, ["strengths", "weaknesses", "missing_points", "contradictions"]),
}


def audit_generated_language(db, group: str, offset: int, limit: int):
    model, fields = GROUPS[group]
    query = select(model.id, *(getattr(model, name) for name in fields)).order_by(model.id)
    if group == "jury_turns":
        query = query.where(model.speaker == "JURY")
    rows = db.execute(query.offset(offset).limit(limit + 1)).mappings().all()
    issues = []
    for row in rows[:limit]:
        texts = []
        for field in fields:
            value = row[field]
            texts.extend(value if isinstance(value, list) else [value or ""])
        if any(foreign_prose(text) for text in texts):
            issues.append(row["id"])
    return {"group": group, "checked": min(len(rows), limit), "foreign_count": len(issues),
            "record_ids": issues, "next_offset": offset + limit if len(rows) > limit else None}
