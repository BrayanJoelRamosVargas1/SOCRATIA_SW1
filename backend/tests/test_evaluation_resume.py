import pytest
from sqlalchemy import select
from test_simulation_sessions import ready_simulation
from app.modules.p3_gestion_simulacion.models import Simulation,SimulationTurn
from app.modules.p4_gestion_evaluacion_resultados.models.evaluation import TurnEvaluation,EvaluationStatus
from app.modules.p4_gestion_evaluacion_resultados.services.evaluation_service import EvaluationService
from app.modules.p4_gestion_evaluacion_resultados.schemas.evaluation import TurnEvaluationResult

@pytest.mark.asyncio
async def test_quota_failure_preserves_completed_turns_and_retry_reuses_them(client,db_session):
    ident=ready_simulation(client,"resume@example.com")
    sim=db_session.get(Simulation,ident)
    for index,question in enumerate(sim.questions[:2],1):
        db_session.add(SimulationTurn(simulation_id=ident,sequence=index,speaker="STUDENT",turn_type="ANSWER",simulation_question_id=question.id,content=f"respuesta {index}"))
    db_session.commit()
    class Fake:
        provider="fake";model="fake";calls=[];fail=True
        async def evaluate_turn(self,**data):
            self.calls.append(data["student_response"])
            if len(self.calls)==2 and self.fail:raise RuntimeError("429 quota PRIVATE KEY")
            return TurnEvaluationResult(classification="PRECISE",score=90,strengths=[],weaknesses=[],missing_points=[],contradictions=[],evidence=[])
    fake=Fake();service=EvaluationService(db_session,evaluator=fake)
    failed=await service.evaluate_simulation(ident)
    assert failed.status==EvaluationStatus.FAILED
    assert "Cuota" in failed.failure_reason and "PRIVATE" not in failed.failure_reason
    assert len(db_session.scalars(select(TurnEvaluation)).all())==1
    fake.fail=False
    done=await service.evaluate_simulation(ident)
    assert done.status==EvaluationStatus.COMPLETED and done.overall_score==90
    assert fake.calls==["respuesta 1","respuesta 2","respuesta 2"]
    assert len(db_session.scalars(select(TurnEvaluation)).all())==2
    await service.evaluate_simulation(ident)
    assert len(fake.calls)==3
