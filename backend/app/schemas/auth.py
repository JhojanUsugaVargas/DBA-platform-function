"""Authentication and Profile Schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    requires_mfa: bool = False


class VerifyOtpRequest(BaseModel):
    username: str
    code: str


class UpdatePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)


class UpdatePhotoRequest(BaseModel):
    photo_base64: str


class ToggleMFARequest(BaseModel):
    mfa_enabled: bool


class UserProfileResponse(BaseModel):
    username: str
    full_name: Optional[str] = None
    role: str
    mfa_enabled: bool
    profile_photo: Optional[str] = None
