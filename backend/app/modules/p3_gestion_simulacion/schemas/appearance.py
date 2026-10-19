from typing import Literal

from pydantic import BaseModel, Field


class AppearanceInput(BaseModel):
    image_base64: str = Field(min_length=16, max_length=500_000)
    torso_in_frame: bool = False


class AppearanceResult(BaseModel):
    person_present: bool
    upper_body_visible: bool
    jacket: bool | None
    collared_shirt: bool | None
    tie: bool | None
    upper_body_covered: bool | None = None
    presentation: Literal["formal", "casual", "incomplete", "uncertain"]
    confidence: float = Field(ge=0, le=1)
    feedback: str = Field(min_length=1, max_length=500)
