from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import get_current_user
from app.modules.p3_gestion_simulacion.repositories.simulation_repository import (
    SimulationRepository,
)
from app.modules.p4_gestion_evaluacion_resultados.schemas.evaluation import EvaluationResponse
from app.modules.p4_gestion_evaluacion_resultados.services.evaluation_service import (
    EvaluationService,
)

router = APIRouter()


@router.post("/simulations/{id}/evaluate", response_model=EvaluationResponse)
async def evaluate_simulation(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sim_repo = SimulationRepository(db)
    simulation = sim_repo.get(id)
    if not simulation or simulation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if simulation.status not in ["COMPLETED", "ABORTED", "ERROR"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Simulation must be completed before evaluation",
        )

    service = EvaluationService(db)
    evaluation = await service.evaluate_simulation(id)
    return evaluation


@router.get("/simulations/{id}/evaluation", response_model=EvaluationResponse)
def get_evaluation(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sim_repo = SimulationRepository(db)
    simulation = sim_repo.get(id)
    if not simulation or simulation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Simulation not found")

    service = EvaluationService(db)
    evaluation = service.repository.get_by_simulation_id(id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    return evaluation


from app.modules.p4_gestion_evaluacion_resultados.schemas.report import SimulationReportResponse
from app.modules.p4_gestion_evaluacion_resultados.services.report_projection_service import (
    ReportProjectionService,
)


@router.get("/simulations/{id}/report", response_model=SimulationReportResponse)
def get_report(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ReportProjectionService.get_simulation_report(db, id, current_user.id)
