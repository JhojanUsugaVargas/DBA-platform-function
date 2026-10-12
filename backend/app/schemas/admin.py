"""Admin Schemas."""
from pydantic import BaseModel, Field


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)
    role: str = "Monitor"


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    mfa_enabled: bool

    class Config:
        from_attributes = True


class ContractCreateRequest(BaseModel):
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
