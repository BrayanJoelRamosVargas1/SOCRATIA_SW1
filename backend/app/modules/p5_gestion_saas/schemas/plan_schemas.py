from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PlanBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: str | None = Field(None, max_length=500)
    price: Decimal = Field(..., ge=0, description="Price must be non-negative")
    max_documents: int = Field(10, ge=0)
    max_simulations: int = Field(10, ge=0)
    max_storage_mb: int = Field(100, ge=0)
    is_active: bool = True

    model_config = ConfigDict(extra="forbid")


class PlanCreate(PlanBase):
    pass


class PlanUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=500)
    price: Decimal | None = Field(None, ge=0)
    max_documents: int | None = Field(None, ge=0)
    max_simulations: int | None = Field(None, ge=0)
    max_storage_mb: int | None = Field(None, ge=0)
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class PlanResponse(PlanBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
