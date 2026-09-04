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

        # 2. Persist the answer
        try:
            snapshot = self.session_service.get_snapshot(self.user, self.simulation_id)
        except Exception:
            raise

        accepted, snapshot = self.session_service.accept_answer(
            self.user,
            self.simulation_id,
            message_id=message_id,
            question_id=snapshot.current_question.id if snapshot.current_question else "",
            content=transcribed_text,
            input_mode=SimulationTurnInputMode.VOICE,
            route_automatically=False,
        )

        if not snapshot.current_question:
            # We already answered the last question? Should not happen if route_automatically=False
            return transcribed_text, fallback_used, None, None, snapshot

        # 3. Jury LLM Router
        logger.info("VOICE_PROCESSING: Starting LiveJuryRouter")

        simulation = self.session_service.simulations.get(self.simulation_id)
        current_question_model = self.session_service.turns.current_question(simulation.id)

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
                tts_stream = await tts.synthesize(tts_request)
            except Exception as e:
                logger.error("TTS Failed: %s", str(e))
                # Continue without TTS (fallback to browser speech synthesis)

        return transcribed_text, fallback_used, action, tts_stream, snapshot
