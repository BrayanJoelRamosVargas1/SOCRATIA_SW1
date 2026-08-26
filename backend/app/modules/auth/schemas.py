from pydantic import BaseModel, EmailStr, Field

from app.modules.users.schemas import UserResponse


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    user: UserResponse


class MessageResponse(BaseModel):
    message: str

