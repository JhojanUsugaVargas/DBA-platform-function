"""Administrative Management Endpoints."""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, role_required
from app.core.security import get_password_hash
from app.db.session import get_db
from app.repositories import user_repo, contract_repo
from app.schemas.admin import (
    UserCreateRequest,
    UserResponse,
    ContractCreateRequest,
    ContractResponse,
    InstanceCreateRequest,
    InstanceResponse
)

router = APIRouter()


@router.post("/users", summary="Create a new user")
def create_user(
    user_req: UserCreateRequest,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Register a new user account (admin only)."""
    if user_repo.get_by_username(db, user_req.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya se encuentra registrado."
        )

    user = user_repo.create_user(
        db=db,
        username=user_req.username,
        full_name=user_req.username,
        hashed_password=get_password_hash(user_req.password),
        role=user_req.role
    )
    return {"success": True, "message": f"Usuario {user.username} creado exitosamente."}


@router.get("/users/all", response_model=List[UserResponse], summary="List all system users")
def list_users(
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """List all registered users (admin only)."""
    return user_repo.list_users(db)


@router.delete("/users/{user_id}", summary="Delete a user")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Remove a user account (cannot delete own account)."""
    user = user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    if user.username == current["username"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propio usuario."
        )

    user_repo.delete_user(db, user)
    return {"success": True, "message": "Usuario eliminado correctamente"}


@router.get("/contracts", response_model=List[ContractResponse], summary="List active contracts")
def list_contracts(
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve all available database contracts."""
    return contract_repo.get_active_contracts(db)


@router.post("/contracts", summary="Create a new contract")
def create_contract(
    req: ContractCreateRequest,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Register a new customer contract (admin only)."""
    contract_dict = contract_repo.add_contract(db, req.name)
    return {"success": True, "contract": contract_dict}


@router.post("/instances", summary="Create a new instance for a contract")
def create_instance(
    req: InstanceCreateRequest,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Register and store an encrypted database instance (admin only)."""
    instance = contract_repo.add_instance(db, req.contract_id, req.name, req.conn_str)
    return {
        "success": True,
        "instance": {
            "id": instance.id,
            "name": instance.name
        }
    }
