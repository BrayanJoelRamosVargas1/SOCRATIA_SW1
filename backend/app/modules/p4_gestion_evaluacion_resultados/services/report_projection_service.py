from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.p3_gestion_simulacion.models.simulation import Simulation, SimulationStatus
from app.modules.p3_gestion_simulacion.models.simulation_turn import SimulationTurn
from app.modules.p4_gestion_evaluacion_resultados.models.evaluation import (
    Evaluation,
    EvaluationStatus,
)
from app.modules.p4_gestion_evaluacion_resultados.schemas.report import (
    ReportQuestionDetail,
    ScoreAvailability,
    SimulationReportResponse,
)


class ReportProjectionService:
    @staticmethod
    def get_simulation_report(
        db: Session, simulation_id: str, user_id: str
    ) -> SimulationReportResponse:
        # Load Simulation and Evaluation
        stmt = (
            select(Simulation)
            .options(
                selectinload(Simulation.document),
                selectinload(Simulation.questions),
                selectinload(Simulation.turns).selectinload(SimulationTurn.simulation_question),
            )
            .where(Simulation.id == simulation_id)
        )
        simulation = db.scalar(stmt)

        if not simulation:
            raise HTTPException(status_code=404, detail="Simulation not found")

        if simulation.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        if simulation.status != SimulationStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Simulation is not completed")

        eval_stmt = (
            select(Evaluation)
            .options(selectinload(Evaluation.turn_evaluations))
            .where(Evaluation.simulation_id == simulation_id)
        )
        evaluation = db.scalar(eval_stmt)

        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        if evaluation.status != EvaluationStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Evaluation is not completed")

        # Map turns to question-answer pairs
        # A question is asked by JURY, answered by STUDENT

        # We need to map simulation_question_id to its QUESTION and ANSWER turns
        question_turns = {
            t.simulation_question_id: t for t in simulation.turns if t.turn_type == "QUESTION"
        }
        answer_turns = {
            t.simulation_question_id: t for t in simulation.turns if t.turn_type == "ANSWER"
        }

        # Map TurnEvaluations
        turn_evals = {te.simulation_turn_id: te for te in evaluation.turn_evaluations}

        report_questions = []
        for sq in sorted(simulation.questions, key=lambda q: q.position):
            q_turn = question_turns.get(sq.id)
            a_turn = answer_turns.get(sq.id)

            if not q_turn or not a_turn:
                continue

            te = turn_evals.get(a_turn.id)

            if te:
                report_questions.append(
                    ReportQuestionDetail(
                        question=q_turn.content,
                        answer=a_turn.content,
                        classification=te.classification,
                        turn_score=te.turn_score,
                        strengths=te.strengths,
                        weaknesses=te.weaknesses,
                        missing_points=te.missing_points,
                        contradictions=te.contradictions,
                        evidence=te.evidence,
                        time_taken_seconds=te.time_taken_seconds,
                        filler_words_count=te.filler_words_count,
                        eye_contact_score=te.eye_contact_score,
                    )
                )

        duration = None
        if simulation.started_at and simulation.finished_at:
            duration = (simulation.finished_at - simulation.started_at).total_seconds() / 60.0

        doc_title = "Untitled"
        if simulation.document:
            doc_title = getattr(simulation.document, "original_name", None) or getattr(simulation.document, "title", "Untitled")

        return SimulationReportResponse(
            simulation_id=simulation.id,
            document_title=doc_title,
            date=simulation.created_at,
            duration_minutes=duration,
            overall_score=evaluation.overall_score,
            content_score=evaluation.content_score,
            communication_score=evaluation.communication_score,
            nonverbal_score=evaluation.nonverbal_score,
            evaluation_version=evaluation.evaluation_version,
            availability=ScoreAvailability(
                content=evaluation.content_score is not None,
                communication=evaluation.communication_score is not None,
                nonverbal=evaluation.nonverbal_score is not None,
            ),
            questions=report_questions,
        )
