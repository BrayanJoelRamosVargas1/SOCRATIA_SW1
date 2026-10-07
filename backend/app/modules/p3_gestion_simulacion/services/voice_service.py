import logging
from collections.abc import AsyncIterator

from sqlalchemy.orm import Session

from app.integrations.llm.dependencies import get_jury_routing_router
from app.integrations.llm.jury_base import JuryAction, JuryRoutingRequest
from app.integrations.stt.base import STTRequest
from app.integrations.stt.dependencies import get_stt_router
from app.integrations.tts.base import TTSRequest
from app.integrations.tts.dependencies import get_tts_provider
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p3_gestion_simulacion.models import SimulationTurnInputMode
from app.modules.p3_gestion_simulacion.schemas.session import SessionSnapshot
from app.modules.p3_gestion_simulacion.services.session_service import SessionService

logger = logging.getLogger(__name__)


class VoiceService:
    def __init__(self, db: Session, user: User, simulation_id: str) -> None:
        self.db = db
        self.user = user
        self.simulation_id = simulation_id
        self.session_service = SessionService(db)

    async def process_utterance(
        self, message_id: str, mime_type: str, audio_bytes: bytes
    ) -> tuple[str, bool, str | None, AsyncIterator[bytes] | None, SessionSnapshot]:
        """
        Process the voice utterance: STT -> LLM Router -> TTS.
        Returns: (transcribed_text, fallback_used, jury_action, tts_stream, snapshot)
        """
        stt = get_stt_router()
        llm = get_jury_routing_router()
        tts = get_tts_provider()

        # 1. STT
        logger.info("VOICE_PROCESSING: Starting STT for message %s", message_id)
        stt_req = STTRequest(audio_bytes=audio_bytes, mime_type=mime_type)
        try:
            transcribed_text, fallback_used, stt_latency = await stt.transcribe(stt_req)
        except Exception as e:
            logger.error("STT Failed: %s", str(e))
            raise

        logger.info("VOICE_PROCESSING: STT complete (%s). Text: %s", stt_latency, transcribed_text)

        from app.modules.p3_gestion_simulacion.models.voice_utterance import (
            VoiceUtterance,
            VoiceUtteranceStatus,
        )
        
        utterance_record = VoiceUtterance(
            simulation_id=self.simulation_id,
            client_utterance_id=message_id,
            mime_type=mime_type,
            status=VoiceUtteranceStatus.COMPLETED,
            stt_fallback_used=fallback_used,
            raw_transcript=transcribed_text,
            stt_latency_ms=stt_latency,
            stt_provider=stt.primary.name if not fallback_used else "gemini"
        )
        self.db.add(utterance_record)

        try:
            snapshot = self.session_service.get_snapshot(self.user, self.simulation_id)
        except Exception:
            raise

        if not transcribed_text.strip():
            logger.warning("VOICE_PROCESSING: Empty audio/silence detected. Rejecting.")
            return transcribed_text, fallback_used, None, None, snapshot

        # 2. Persist the answer
        accepted, snapshot_after = self.session_service.accept_answer(
            self.user,
            self.simulation_id,
            message_id=message_id,
            question_id=snapshot.current_question.id if snapshot.current_question else "",
            content=transcribed_text,
            input_mode=SimulationTurnInputMode.VOICE,
            route_automatically=False,
        )

        # 3. Jury LLM Router
        logger.info("VOICE_PROCESSING: Starting LiveJuryRouter")

        from app.modules.p3_gestion_simulacion.models import SimulationQuestion
        
        simulation = self.session_service.simulations.get(self.simulation_id)
        current_question_model = self.db.get(SimulationQuestion, snapshot.current_question.id) if snapshot.current_question else None

        if current_question_model and current_question_model.question:
            expected_points = current_question_model.question.expected_answer_points
        else:
            expected_points = []

        llm_request = JuryRoutingRequest(
            question_text=snapshot.current_question.text,
            expected_answer_points=expected_points,
            student_answer=transcribed_text,
            focus_type=simulation.jury_profile.focus_type.value,
            strictness=simulation.jury_profile.strictness,
            interruption_level=simulation.jury_profile.interruption_level.value,
        )

        try:
            llm_result = await llm.route(llm_request)
            decision = llm_result.decision
            action = decision.action.value
            logger.info("VOICE_PROCESSING: LiveJuryRouter decided: %s", action)
            
            # Enforce Capa IA follow-up depth limit
            depth = current_question_model.follow_up_depth if current_question_model else 0
            if action == JuryAction.FOLLOW_UP.value and depth >= 2:
                logger.info("VOICE_PROCESSING: Follow-up depth >= 2, forcing NEXT_BANK")
                action = JuryAction.NEXT_BANK.value
                decision = None
                
        except Exception as e:
            logger.error("LiveJuryRouter failed, falling back to NEXT_BANK: %s", str(e))
            action = JuryAction.NEXT_BANK.value
            decision = None

        # 4. Commit Jury decision to DB
        if action == JuryAction.FOLLOW_UP.value and decision and decision.follow_up_question:
            turn, snapshot = self.session_service.add_follow_up_question(
                self.user,
                self.simulation_id,
                text=decision.follow_up_question,
                parent_question_id=snapshot.current_question.id,
            )
        else:
            turn, snapshot = self.session_service.proceed_to_next_bank_question(
                self.user, self.simulation_id
            )

        # 5. TTS for the jury question
        tts_stream = None
        if turn and turn.content:
            tts_request = TTSRequest(text=turn.content)
            try:
                tts_stream = tts.synthesize(tts_request)
            except Exception as e:
                logger.error("TTS generation failed: %s", str(e))

        return transcribed_text, fallback_used, action, tts_stream, snapshot
