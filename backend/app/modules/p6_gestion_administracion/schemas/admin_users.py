
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminUserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    is_active: bool | None = None
    roles: list[str] | None = None

class PaginatedUsersResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    size: int
    pages: int
