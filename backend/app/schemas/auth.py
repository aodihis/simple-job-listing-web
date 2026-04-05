from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr = Field(description="Admin email address. Must be unique.")
    display_name: str = Field(min_length=1, max_length=100, description="Display name shown in the dashboard.")
    password: str = Field(min_length=8, description="Password. Minimum 8 characters.")


class LoginRequest(BaseModel):
    email: EmailStr = Field(description="Admin email address.")
    password: str = Field(description="Admin password.")


class TokenResponse(BaseModel):
    access_token: str = Field(description="JWT access token. Pass as 'Authorization: Bearer <token>'.")
    token_type: str = Field(default="bearer", description="Always 'bearer'.")
    expires_in: int = Field(description="Token lifetime in seconds.")


class AdminUserRead(BaseModel):
    public_id: str
    email: str
    display_name: str
    is_active: bool

    model_config = {"from_attributes": True}
