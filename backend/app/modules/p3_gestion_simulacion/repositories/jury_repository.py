from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.p3_gestion_simulacion.models import (
    FocusType,
    InterruptionLevel,
    JuryProfile,
)

DEFAULT_JURY_PROFILES = (
    (
        "00000000-0000-4000-8000-000000000001",
        "Jurado Metodológico",
        "Cuestiona metodología, validación y diseño del estudio.",
        FocusType.METHODOLOGICAL,
        3,
        InterruptionLevel.LOW,
    ),
    (
        "00000000-0000-4000-8000-000000000002",
        "Jurado Técnico",
        "Profundiza en arquitectura, decisiones e implementación.",
        FocusType.TECHNICAL,
        4,
        InterruptionLevel.MEDIUM,
    ),
    (
        "00000000-0000-4000-8000-000000000003",
        "Jurado Crítico",
        "Busca inconsistencias, riesgos y debilidades de la propuesta.",
        FocusType.CRITICAL,
        5,
        InterruptionLevel.HIGH,
    ),
)


class JuryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ensure_defaults(self) -> None:
        existing = set(self.db.scalars(select(JuryProfile.id)))
        for profile in DEFAULT_JURY_PROFILES:
            if profile[0] not in existing:
                self.db.add(
                    JuryProfile(
                        id=profile[0],
                        name=profile[1],
                        description=profile[2],
                        focus_type=profile[3],
                        strictness=profile[4],
                        interruption_level=profile[5],
                        is_active=True,
                    )
                )
        self.db.flush()

    def list_active(self) -> list[JuryProfile]:
        statement = (
            select(JuryProfile)
            .where(JuryProfile.is_active.is_(True))
            .order_by(JuryProfile.id)
        )
        return list(self.db.scalars(statement))

    def get_active(self, profile_id: str) -> JuryProfile | None:
        return self.db.scalar(
            select(JuryProfile).where(
                JuryProfile.id == profile_id,
                JuryProfile.is_active.is_(True),
            )
        )
