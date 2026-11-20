from pydantic import BaseModel, ConfigDict, Field


class DocumentSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str = Field(min_length=3, max_length=400)


class DocumentSearchMatch(BaseModel):
    fragment: int
    excerpt: str


class DocumentSearchResponse(BaseModel):
    engine: str
    model: str | None
    degraded: bool
    matches: list[DocumentSearchMatch]
