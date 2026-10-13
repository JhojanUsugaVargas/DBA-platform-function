"""Admin Schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: str = "Monitor"


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None


class UserChangePasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, description="Contraseña segura de mínimo 8 caracteres")


class MaintenanceStatusRequest(BaseModel):
    is_active: bool
    title: Optional[str] = None
    subtitle: Optional[str] = None
    disabled_modules: Optional[list] = None


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: str
    mfa_enabled: bool

    class Config:
        from_attributes = True


class ContractCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ContractUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ContractResponse(BaseModel):
    id: int
    name: str
    is_active: bool = True

    class Config:
        from_attributes = True


class InstanceCreateRequest(BaseModel):
    contract_id: int
    name: str = Field(min_length=1, max_length=100)
    conn_str: str = Field(min_length=1)


class InstanceResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
