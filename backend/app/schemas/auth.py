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
    new_password: str = Field(min_length=8, description="Contraseña segura de mínimo 8 caracteres")


class UpdatePhotoRequest(BaseModel):
    photo_base64: str = Field(max_length=2_800_000, description="Imagen data URL (máx. ~2 MB)")
    rights_confirmed: bool = Field(default=False, description="El usuario declara tener derechos sobre la imagen")


class ToggleMFARequest(BaseModel):
    mfa_enabled: bool


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1)


class UserProfileResponse(BaseModel):
    username: str
    full_name: Optional[str] = None
    role: str
    mfa_enabled: bool
    profile_photo: Optional[str] = None
    email_opt_out: bool = False
    consent_required: bool = False
    legal_version: Optional[str] = None
