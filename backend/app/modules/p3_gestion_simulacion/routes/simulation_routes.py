from typing import Annotated

from fastapi import APIRouter, Depends, Response, HTTPException, status
from pydantic import BaseModel, Field
from app.integrations.tts.base import TTSRequest, TTSProviderError
from app.integrations.tts.dependencies import get_tts_provider
from app.integrations.tts.local_tts import speech_segments
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.modules.p3_gestion_simulacion.schemas.appearance import AppearanceInput, AppearanceResult
from app.modules.p3_gestion_simulacion.services.appearance_service import AppearanceService
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import CurrentUser
from app.modules.p3_gestion_simulacion.schemas.session import SessionSnapshot
from app.modules.p3_gestion_simulacion.schemas.simulation import (
    CalibrationInput,
    JuryProfileResponse,
    SimulationCreateInput,
    SimulationResponse,
)
from app.modules.p3_gestion_simulacion.services.session_service import SessionService
from app.modules.p3_gestion_simulacion.repositories.turn_repository import TurnRepository
from app.modules.p3_gestion_simulacion.services.simulation_service import (
    SimulationService,
)

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]


@router.get("/voice-capabilities")
def voice_capabilities(current_user: CurrentUser):
    del current_user
    settings=get_settings()
    return {"local_audio":bool(settings.voice_tts_enabled and settings.local_tts_enabled)}


class JurySpeechInput(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    segment_index: int | None = Field(default=None, ge=0, le=100)


@router.post("/simulations/{simulation_id}/speech/prewarm", status_code=204)
async def prewarm_jury_speech(simulation_id: str, current_user: CurrentUser, db: Database):
    snapshot = SessionService(db).get_snapshot(current_user, simulation_id)
    settings = get_settings()
    if snapshot.status != "ACTIVE" or not settings.local_tts_enabled or not settings.voice_tts_enabled:
        return Response(status_code=204)
    question = TurnRepository(db).next_pending_question(simulation_id)
    # One existing bank question only. Never speculate with a paid LLM or expose
    # the next question's content to the browser before its turn.
    text = (question.prompt_text or (question.question.question if question.question else "")) if question else ""
    if question and question.source == "BANK" and text and len(text) <= 800:
        try:
            for segment in speech_segments(text):
                async for _chunk in get_tts_provider().synthesize(TTSRequest(text=segment, speaker_index=question.position % 3)):
                    pass
        except TTSProviderError:
            pass
    return Response(status_code=204)


@router.post("/simulations/{simulation_id}/speech")
async def jury_speech(simulation_id: str, body: JurySpeechInput, current_user: CurrentUser, db: Database):
    snapshot = SessionService(db).get_snapshot(current_user, simulation_id)
    question = snapshot.current_question
    if not question or snapshot.status == "COMPLETED":
        raise HTTPException(409, "No hay una pregunta activa")
    greetings = ["", "Bienvenido a tu defensa. Comencemos. ", "Bienvenido de nuevo. Continuemos tu defensa desde la pregunta pendiente. ", "Bienvenido a tu defensa. Somos tu tribunal. Te haremos preguntas sobre tu investigación y escucharemos tus respuestas. Tómate un momento para organizar tus ideas. Comencemos. "]
    if body.text not in {greeting + question.text for greeting in greetings}:
        raise HTTPException(422, "La voz solo puede leer la pregunta activa")
    settings = get_settings()
    if not settings.voice_tts_enabled or not settings.local_tts_enabled:
        raise HTTPException(503, "Voz local no habilitada")
    provider = get_tts_provider()
    segments = speech_segments(body.text)
    if body.segment_index is not None and body.segment_index >= len(segments):
        raise HTTPException(422, "Segmento de voz inválido")
    text = body.text if body.segment_index is None else segments[body.segment_index]
    try:
        data = b"".join([chunk async for chunk in provider.synthesize(TTSRequest(text=text, speaker_index=(question.position - 1) % 3))])
    except TTSProviderError:
        raise HTTPException(503, "Voz local no disponible") from None
    return Response(data, media_type=provider.mime_type, headers={"Cache-Control": "no-store", "X-Speech-Segments": str(len(segments))})


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


@router.post("/simulations/{simulation_id}/start", response_model=SessionSnapshot)
def start_simulation(
    simulation_id: str,
    current_user: CurrentUser,
    db: Database,
) -> SessionSnapshot:
    return SessionService(db).start(current_user, simulation_id)


@router.get("/simulations/{simulation_id}/session", response_model=SessionSnapshot)
def get_simulation_session(
    simulation_id: str,
    current_user: CurrentUser,
    db: Database,
) -> SessionSnapshot:
    return SessionService(db).get_snapshot(current_user, simulation_id)


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


@router.post("/simulations/{simulation_id}/appearance", response_model=AppearanceResult)
def analyze_appearance(
    simulation_id: str, body: AppearanceInput, current_user: CurrentUser, db: Database,
) -> AppearanceResult:
    SimulationService(db).get_for(current_user, simulation_id)
    return AppearanceService(get_settings()).analyze(body.image_base64, torso_in_frame=body.torso_in_frame)
