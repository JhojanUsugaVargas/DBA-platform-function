"""Admin Schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: str = "Monitor"
    consent_confirmed: bool = False  # el admin confirma autorización del titular para registrar su correo


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


class IncidentCreateRequest(BaseModel):
    ticket_type: str = "Incidente"  # "Incidente", "Requerimiento", "Soporte"
    module: str = "General"  # "General", "Base de Datos", "Almacenamiento", etc.
    priority: str = "Media"  # "Crítica", "Alta", "Media", "Baja"
    title: Optional[str] = None
    description: str = Field(min_length=3)
    username: Optional[str] = None
    status: str = "Abierto"  # "Abierto", "En Progreso", "Resuelto", "Cerrado"
    notes: Optional[str] = ""


class IncidentUpdateRequest(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[str] = None
    module: Optional[str] = None
    ticket_type: Optional[str] = None
    description: Optional[str] = None


class IncidentResponse(BaseModel):
    id: int
    user_id: int
    username: str
    user_full_name: Optional[str] = None
    user_email: Optional[str] = None
    rating: int = 0
    comment: Optional[str] = None
    ticket_type: str = "Incidente"
    module: str = "General"
    priority: str = "Media"
    description: str
    status: str = "Abierto"
    notes: Optional[str] = ""
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class IncidentStatsResponse(BaseModel):
    total: int = 0
    open: int = 0
    in_progress: int = 0
    resolved: int = 0
    closed: int = 0
    incidents_count: int = 0
    requirements_count: int = 0


class IncidentListResponse(BaseModel):
    incidents: list[IncidentResponse]
    stats: IncidentStatsResponse

