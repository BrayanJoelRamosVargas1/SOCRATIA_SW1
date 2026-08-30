from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import CurrentUser
from app.modules.p3_gestion_simulacion.schemas.simulation import (
    CalibrationInput,
    JuryProfileResponse,
    SimulationCreateInput,
    SimulationResponse,
)
from app.modules.p3_gestion_simulacion.services.simulation_service import SimulationService

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]


@router.get("/jury-profiles", response_model=list[JuryProfileResponse])
def list_jury_profiles(current_user: CurrentUser, db: Database) -> list[JuryProfileResponse]:
    del current_user
    profiles = SimulationService(db).list_jury_profiles()
    return [JuryProfileResponse.model_validate(profile) for profile in profiles]


@router.post("/simulations", response_model=SimulationResponse, status_code=status.HTTP_201_CREATED)
def create_simulation(
    body: SimulationCreateInput,
    current_user: CurrentUser,
    db: Database,
) -> SimulationResponse:
    simulation = SimulationService(db).create(
        current_user,
        document_id=body.document_id,
        jury_profile_id=body.jury_profile_id,
        planned_duration_minutes=body.planned_duration_minutes,
    )
    return SimulationResponse.model_validate(simulation)


@router.get("/simulations", response_model=list[SimulationResponse])
def list_simulations(current_user: CurrentUser, db: Database) -> list[SimulationResponse]:
    simulations = SimulationService(db).list_for(current_user)
    return [SimulationResponse.model_validate(item) for item in simulations]


@router.get("/simulations/{simulation_id}", response_model=SimulationResponse)
def get_simulation(
    simulation_id: str,
    current_user: CurrentUser,
    db: Database,
) -> SimulationResponse:
    simulation = SimulationService(db).get_for(current_user, simulation_id)
    return SimulationResponse.model_validate(simulation)


@router.put("/simulations/{simulation_id}/calibration", response_model=SimulationResponse)
def save_calibration(
    simulation_id: str,
    body: CalibrationInput,
    current_user: CurrentUser,
    db: Database,
) -> SimulationResponse:
    simulation = SimulationService(db).calibrate(
        current_user,
        simulation_id,
        camera_ready=body.camera_ready,
        microphone_ready=body.microphone_ready,
        vision_ready=body.vision_ready,
    )
    return SimulationResponse.model_validate(simulation)


@router.delete("/simulations/{simulation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_simulation(
    simulation_id: str,
    current_user: CurrentUser,
    db: Database,
) -> Response:
    SimulationService(db).delete_for(current_user, simulation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
