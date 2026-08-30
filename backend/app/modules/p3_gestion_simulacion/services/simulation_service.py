from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.models.document import Document, DocumentStatus
from app.modules.p2_gestion_documentos_preparacion.models.question_bank import (
    QuestionBank,
    QuestionBankStatus,
)
from app.modules.p3_gestion_simulacion.exceptions import (
    InvalidSimulationTransitionError,
    JuryProfileNotFoundError,
    SimulationCannotBeDeletedError,
    SimulationDocumentNotReadyError,
)
from app.modules.p3_gestion_simulacion.models import (
    JuryProfile,
    Simulation,
    SimulationQuestion,
    SimulationQuestionSource,
    SimulationQuestionStatus,
    SimulationStatus,
)
from app.modules.p3_gestion_simulacion.policies.simulation_policy import SimulationPolicy
from app.modules.p3_gestion_simulacion.repositories.jury_repository import JuryRepository
from app.modules.p3_gestion_simulacion.repositories.simulation_repository import (
    SimulationRepository,
)

ALLOWED_TRANSITIONS = {
    SimulationStatus.DRAFT: {SimulationStatus.READY, SimulationStatus.ERROR},
    SimulationStatus.READY: {
        SimulationStatus.DRAFT,
        SimulationStatus.ACTIVE,
        SimulationStatus.ERROR,
    },
    SimulationStatus.ACTIVE: {
        SimulationStatus.COMPLETED,
        SimulationStatus.ABORTED,
        SimulationStatus.ERROR,
    },
    SimulationStatus.COMPLETED: set(),
    SimulationStatus.ABORTED: set(),
    SimulationStatus.ERROR: set(),
}


class SimulationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.simulations = SimulationRepository(db)
        self.juries = JuryRepository(db)

    def list_jury_profiles(self) -> list[JuryProfile]:
        self.juries.ensure_defaults()
        self.db.commit()
        return self.juries.list_active()

    def create(
        self,
        user: User,
        *,
        document_id: str,
        jury_profile_id: str,
        planned_duration_minutes: int,
    ) -> Simulation:
        document = self.db.get(Document, document_id)
        if document is None or document.user_id != user.id:
            from app.modules.p2_gestion_documentos_preparacion.exceptions import (
                DocumentNotFoundError,
            )

            raise DocumentNotFoundError
        if document.status != DocumentStatus.PROCESSED:
            raise SimulationDocumentNotReadyError
        bank = self.db.scalar(
            select(QuestionBank).where(
                QuestionBank.document_id == document.id,
                QuestionBank.status == QuestionBankStatus.READY,
            )
        )
        if bank is None or len(bank.questions) != 12:
            raise SimulationDocumentNotReadyError
        self.juries.ensure_defaults()
        jury = self.juries.get_active(jury_profile_id)
        if jury is None:
            raise JuryProfileNotFoundError

        simulation = Simulation(
            user_id=user.id,
            document_id=document.id,
            question_bank_id=bank.id,
            jury_profile_id=jury.id,
            status=SimulationStatus.DRAFT,
            planned_duration_minutes=planned_duration_minutes,
        )
        simulation.questions.extend(
            SimulationQuestion(
                question_id=question.id,
                position=position,
                source=SimulationQuestionSource.BANK,
                status=SimulationQuestionStatus.PENDING,
            )
            for position, question in enumerate(bank.questions)
        )
        self.simulations.add(simulation)
        self.db.commit()
        self.db.refresh(simulation)
        return simulation

    def list_for(self, user: User) -> list[Simulation]:
        return self.simulations.list_for_user(user.id)

    def get_for(self, user: User, simulation_id: str) -> Simulation:
        return SimulationPolicy.can_read(user, self.simulations.get(simulation_id))

    def delete_for(self, user: User, simulation_id: str) -> None:
        simulation = SimulationPolicy.can_delete(user, self.simulations.get(simulation_id))
        if simulation.status not in {SimulationStatus.DRAFT, SimulationStatus.READY}:
            raise SimulationCannotBeDeletedError
        self.simulations.delete(simulation)
        self.db.commit()

    def transition(self, simulation: Simulation, target: SimulationStatus) -> None:
        if target == simulation.status:
            return
        if target not in ALLOWED_TRANSITIONS[simulation.status]:
            raise InvalidSimulationTransitionError
        simulation.status = target

    def calibrate(
        self,
        user: User,
        simulation_id: str,
        *,
        camera_ready: bool,
        microphone_ready: bool,
        vision_ready: bool,
    ) -> Simulation:
        simulation = SimulationPolicy.can_calibrate(
            user, self.simulations.get(simulation_id, for_update=True)
        )
        if simulation.status not in {SimulationStatus.DRAFT, SimulationStatus.READY}:
            raise InvalidSimulationTransitionError
        simulation.camera_ready = camera_ready
        simulation.microphone_ready = microphone_ready
        simulation.vision_ready = vision_ready
        target = (
            SimulationStatus.READY
            if camera_ready and microphone_ready and vision_ready
            else SimulationStatus.DRAFT
        )
        self.transition(simulation, target)
        self.db.commit()
        self.db.refresh(simulation)
        return simulation
