from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.p5_gestion_saas.models.subscription import SubscriptionStatus


class SubscriptionCreate(BaseModel):
    user_id: str = Field(..., max_length=36)
    plan_id: str = Field(..., max_length=36)

    model_config = ConfigDict(extra="forbid")


class SubscriptionUpdate(BaseModel):
    status: SubscriptionStatus | None = None
    # We might not allow updating plan directly here or maybe yes? Wait, "asignar plan, cambiar plan".
    plan_id: str | None = Field(None, max_length=36)

    model_config = ConfigDict(extra="forbid")


class SubscriptionResponse(BaseModel):
    id: str
    user_id: str
    plan_id: str
    status: SubscriptionStatus
    price_at_subscription: Decimal
    started_at: datetime
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class StudentSubscriptionCreate(BaseModel):
    plan_id: str = Field(..., max_length=36)

    model_config = ConfigDict(extra="forbid")


class StudentSubscriptionChange(BaseModel):
    plan_id: str = Field(..., max_length=36)

    model_config = ConfigDict(extra="forbid")


from app.modules.p5_gestion_saas.schemas.plan_schemas import PlanResponse


class StudentCurrentSubscriptionResponse(BaseModel):
    subscription: SubscriptionResponse | None = None
    plan: PlanResponse | None = None
    history: list[SubscriptionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

