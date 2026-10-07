from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.p2_gestion_documentos_preparacion.models.document import DocumentChunk
from app.modules.p3_gestion_simulacion.models.simulation import Simulation
from app.modules.p3_gestion_simulacion.models.simulation_turn import (
    SimulationTurn,
    SimulationTurnType,
)
from app.modules.p4_gestion_evaluacion_resultados.models.evaluation import (
    Evaluation,
    EvaluationStatus,
    TurnEvaluation,
)
from app.modules.p4_gestion_evaluacion_resultados.repositories.evaluation_repository import (
    EvaluationRepository,
)
from app.modules.p4_gestion_evaluacion_resultados.services.evaluator import Evaluator


class EvaluationService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = EvaluationRepository(db)
        self.evaluator = Evaluator()

    async def evaluate_simulation(self, simulation_id: str) -> Evaluation:
        # Idempotency check
        existing = self.repository.get_by_simulation_id(simulation_id)
        if existing:
            if existing.status == EvaluationStatus.PROCESSING:
                from fastapi import HTTPException
                raise HTTPException(status_code=409, detail="Evaluation is already processing.")
            if existing.status == EvaluationStatus.COMPLETED:
                return existing
            if existing.status == EvaluationStatus.FAILED:
                evaluation = existing
                evaluation.status = EvaluationStatus.PROCESSING
                evaluation.started_at = datetime.now()
                self.db.commit()
            else:
                evaluation = existing
        else:
            # Create pending evaluation
            evaluation = Evaluation(
                simulation_id=simulation_id,
                status=EvaluationStatus.PROCESSING,
                started_at=datetime.now(),
            )
            self.repository.create(evaluation)

        try:
            # Fetch Simulation
            stmt = select(Simulation).where(Simulation.id == simulation_id)
            simulation = self.db.execute(stmt).scalar_one_or_none()
            if not simulation:
                raise ValueError("Simulation not found")

            # Fetch Context (tenant isolation by document_id)
            chunks_stmt = (
                select(DocumentChunk)
                .where(DocumentChunk.document_id == simulation.document_id)
                .order_by(DocumentChunk.chunk_index)
            )
            chunks = self.db.scalars(chunks_stmt).all()
            context_text = "\n\n".join([c.content for c in chunks])

            # Process turns
            stmt_turns = (
                select(SimulationTurn)
                .where(SimulationTurn.simulation_id == simulation_id)
                .order_by(SimulationTurn.sequence)
            )
            turns = self.db.scalars(stmt_turns).all()

            turn_evals = []
            total_score = 0.0
            count = 0

            # Map questions
            questions_map = {q.id: q for q in simulation.questions}
            bank_questions_map = {q.id: q.question for q in simulation.questions if q.question}

            for turn in turns:
                if turn.turn_type == SimulationTurnType.ANSWER and turn.speaker == "STUDENT":
                    question_id = turn.simulation_question_id
                    sim_question = questions_map.get(question_id) if question_id else None

                    if not sim_question:
                        continue

                    # Find parent question context if follow up
                    expected_points = None
                    if sim_question.source == "FOLLOW_UP":
                        parent = sim_question.parent_question
                        if parent and parent.question:
                            expected_points = parent.question.expected_answer_points
                    else:
                        if sim_question.question:
                            expected_points = sim_question.question.expected_answer_points

                    # Evaluate turn
                    result = await self.evaluator.evaluate_turn(
                        question=sim_question.prompt_text or sim_question.question.question
                        if sim_question.question
                        else "N/A",
                        student_response=turn.content,
                        context_text=context_text,
                        expected_points=expected_points,
                    )

                    turn_eval = TurnEvaluation(
                        evaluation_id=evaluation.id,
                        simulation_turn_id=turn.id,
                        source_question_id=question_id,
                        classification=result.classification,
                        turn_score=result.score,
                        strengths=result.strengths,
                        weaknesses=result.weaknesses,
                        missing_points=result.missing_points,
                        contradictions=result.contradictions,
                        evidence=result.evidence,
                        provider_used=self.evaluator.provider,
                        model_used=self.evaluator.model,
                        evaluation_version="v1",
                    )
                    self.db.add(turn_eval)
                    turn_evals.append(turn_eval)
                    total_score += result.score
                    count += 1

            # Update overall scores
            evaluation.content_score = (total_score / count) if count > 0 else 0.0
            # Dimensions logic: communication and nonverbal are NULL as per P3 requirements
            evaluation.communication_score = None
            evaluation.nonverbal_score = None
            evaluation.overall_score = evaluation.content_score

            evaluation.status = EvaluationStatus.COMPLETED
            evaluation.completed_at = datetime.now()
            evaluation.provider_used = self.evaluator.provider
            evaluation.model_used = self.evaluator.model
            evaluation.evaluation_version = "v1"

            self.db.commit()

        except Exception as e:
            self.db.rollback()
            print("ERROR IN EVALUATION SERVICE:", e)
            
            # Fetch again to avoid DetachedInstanceError
            evaluation = self.db.query(Evaluation).filter_by(id=evaluation.id).first()
            if evaluation:
                evaluation.status = EvaluationStatus.FAILED
                evaluation.failure_reason = str(e)
                evaluation.completed_at = datetime.now()
                self.db.commit()

        # Refresh from db to get relationships loaded
        self.db.refresh(evaluation)
        return evaluation
