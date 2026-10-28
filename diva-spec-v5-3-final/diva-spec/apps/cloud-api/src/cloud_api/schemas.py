"""Request and response schemas for the cloud auth API (TASK-PUB-01)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Role = Literal["owner", "admin", "staff"]


class BootstrapRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class MfaSetupRequest(BaseModel):
    email: EmailStr
    password: str


class MfaEnableRequest(BaseModel):
    email: EmailStr
    password: str
    code: str = Field(min_length=6, max_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp: str | None = None
    recovery_code: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: Role = "staff"


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class MfaSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str


class MfaEnableResponse(BaseModel):
    recovery_codes: list[str]


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    mfa_enabled: bool
    is_active: bool
    created_at: datetime


class AuditOut(BaseModel):
    id: int
    actor: str | None
    action: str
    target: str | None
    result: str
    ip: str | None
    created_at: datetime
