import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.p3_gestion_simulacion.models import JuryProfile, Simulation
from app.modules.p3_gestion_simulacion.repositories.jury_repository import JuryRepository
from app.modules.p3_gestion_simulacion.schemas.simulation import (
    JuryProfileCreateInput,
    JuryProfileUpdateInput,
)


class AdminJuryProfileService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.juries = JuryRepository(db)

    def list_all(self) -> list[JuryProfile]:
        self.juries.ensure_defaults()
        self.db.commit()
        return self.juries.list_all()

    def get(self, profile_id: str) -> JuryProfile:
        profile = self.juries.get(profile_id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jury profile not found")
        return profile

    def create(self, data: JuryProfileCreateInput) -> JuryProfile:
        # Check if name is unique
        existing = self.db.scalar(select(JuryProfile).where(JuryProfile.name == data.name))
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Jury profile name already exists")
        
        profile = JuryProfile(
            id=str(uuid.uuid4()),
            name=data.name,
            description=data.description,
            focus_type=data.focus_type,
            strictness=data.strictness,
            interruption_level=data.interruption_level,
            is_active=data.is_active,
        )
        self.juries.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update(self, profile_id: str, data: JuryProfileUpdateInput) -> JuryProfile:
        profile = self.get(profile_id)
        
        if data.name is not None and data.name != profile.name:
            existing = self.db.scalar(select(JuryProfile).where(JuryProfile.name == data.name))
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Jury profile name already exists")
            profile.name = data.name
            
        if data.description is not None:
            profile.description = data.description
        if data.focus_type is not None:
            profile.focus_type = data.focus_type
        if data.strictness is not None:
            profile.strictness = data.strictness
        if data.interruption_level is not None:
            profile.interruption_level = data.interruption_level
        if data.is_active is not None:
            profile.is_active = data.is_active

        self.db.commit()
        self.db.refresh(profile)
        return profile

    def delete(self, profile_id: str) -> None:
        profile = self.get(profile_id)
        
        # Check if used in simulations
        has_simulations = self.db.scalar(select(Simulation.id).where(Simulation.jury_profile_id == profile_id).limit(1))
        if has_simulations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Cannot delete jury profile because it has associated simulations. You can deactivate it instead."
            )
            
        self.juries.delete(profile)
        self.db.commit()
