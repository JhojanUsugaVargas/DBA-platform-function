"""Administrative Management Endpoints."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, role_required
from app.core.security import get_password_hash, create_unsubscribe_token
from app.core.config import settings
from app.db.session import get_db
from app.repositories import user_repo, contract_repo, audit_repo, feedback_repo
from app.services import email_service, maintenance_service, privacy_service
from app.services.remote_db_service import test_remote_connection
from app.schemas.admin import (
    UserCreateRequest,
    UserUpdateRequest,
    UserChangePasswordRequest,
    MaintenanceStatusRequest,
    UserResponse,
    ContractCreateRequest,
    ContractUpdateRequest,
    ContractResponse,
    InstanceCreateRequest,
    InstanceResponse,
    IncidentCreateRequest,
    IncidentUpdateRequest,
    IncidentResponse,
    IncidentListResponse,
    IncidentStatsResponse
)

router = APIRouter()


@router.post("/users", summary="Create a new user with invitation email")
def create_user(
    user_req: UserCreateRequest,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Register a new user account with custom password and optional invitation email."""
    admin_username = _.get("username", "admin") if isinstance(_, dict) else "admin"

    if user_repo.get_by_username(db, user_req.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya se encuentra registrado."
        )

    has_email = bool(user_req.email and user_req.email.strip())
    if has_email and not user_req.consent_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes confirmar que cuentas con la autorización del titular para registrar sus datos personales."
        )

    raw_password = user_req.password if user_req.password and user_req.password.strip() else "ChangeMe123!"
    user = user_repo.create_user(
        db=db,
        username=user_req.username,
        full_name=user_req.full_name or user_req.username,
        hashed_password=get_password_hash(raw_password),
        role=user_req.role,
        email=user_req.email
    )

    invitation = None
    if has_email:
        invitation = email_service.send_user_invitation(
            to_email=user_req.email.strip(),
            username=user.username,
            full_name=user.full_name or user.username,
            password=raw_password,
            role=user.role,
            unsubscribe_url=f"{settings.PUBLIC_API_URL}/auth/unsubscribe?token={create_unsubscribe_token(user.username)}"
        )

    audit_repo.log_action(
        db=db,
        username=admin_username,
        action="CREATE_USER",
        status="SUCCESS",
        details=f"Usuario '{user.username}' creado con rol {user.role}. Correo registrado: {'sí' if has_email else 'no'}; autorización del titular confirmada: {'sí' if user_req.consent_confirmed else 'n/a'}."
    )

    return {
        "success": True,
        "message": f"Usuario {user.username} creado exitosamente.",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        },
        "invitation": invitation
    }


@router.put("/users/{user_id}/password", summary="Change user password (admin only)")
def change_user_password_endpoint(
    user_id: int,
    req: UserChangePasswordRequest,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Allows administrator to reset or change the password for any user."""
    admin_username = _.get("username", "admin") if isinstance(_, dict) else "admin"

    target_user = user_repo.get_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    hashed = get_password_hash(req.new_password)
    user_repo.update_user_password(db, user_id, hashed)

    audit_repo.log_action(
        db=db,
        username=admin_username,
        action="CHANGE_USER_PASSWORD",
        status="SUCCESS",
        details=f"Contraseña cambiada por el admin para el usuario '{target_user.username}'."
    )

    return {
        "success": True,
        "message": f"Contraseña actualizada exitosamente para el usuario '{target_user.username}'."
    }


@router.put("/users/{user_id}", summary="Update user details (admin only)")
def update_user_endpoint(
    user_id: int,
    req: UserUpdateRequest,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Update profile details (name, email, role) for an existing user."""
    admin_username = _.get("username", "admin") if isinstance(_, dict) else "admin"

    user = user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    updated_user = user_repo.update_user_details(
        db=db,
        user_id=user_id,
        full_name=req.full_name,
        email=req.email,
        role=req.role
    )

    audit_repo.log_action(
        db=db,
        username=admin_username,
        action="UPDATE_USER",
        status="SUCCESS",
        details=f"Usuario '{user.username}' actualizado: rol='{updated_user.role}', correo registrado: {'sí' if updated_user.email else 'no'}."
    )

    return {
        "success": True,
        "message": f"Usuario '{user.username}' actualizado correctamente.",
        "user": {
            "id": updated_user.id,
            "username": updated_user.username,
            "full_name": updated_user.full_name,
            "email": updated_user.email,
            "role": updated_user.role
        }
    }


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
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Remove a user account (cannot delete own account)."""
    admin_username = _.get("username", "admin") if isinstance(_, dict) else "admin"

    user = user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    if user.username == admin_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propio usuario."
        )

    deleted_username = user.username
    privacy_service.erase_user(db, user)
    audit_repo.log_action(
        db=db,
        username=admin_username,
        action="DELETE_USER",
        status="SUCCESS",
        details=f"Usuario '{deleted_username}' eliminado por el admin."
    )
    return {"success": True, "message": f"Usuario {deleted_username} eliminado correctamente"}


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
    username = _.get("username", "admin") if isinstance(_, dict) else "admin"
    contract_dict = contract_repo.add_contract(db, req.name)
    audit_repo.log_action(
        db=db,
        username=username,
        action="CREATE_CONTRACT",
        contract_name=req.name,
        status="SUCCESS",
        details=f"Contrato '{req.name}' creado exitosamente."
    )
    return {"success": True, "contract": contract_dict}


@router.put("/contracts/{contract_id}", summary="Update a contract")
def update_contract_endpoint(
    contract_id: int,
    req: ContractUpdateRequest,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Update contract name (admin only)."""
    username = _.get("username", "admin") if isinstance(_, dict) else "admin"
    contract_dict = contract_repo.update_contract(db, contract_id, req.name)
    if not contract_dict:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato no encontrado.")

    audit_repo.log_action(
        db=db,
        username=username,
        action="UPDATE_CONTRACT",
        contract_name=req.name,
        status="SUCCESS",
        details=f"Contrato ID {contract_id} actualizado a '{req.name}'."
    )
    return {"success": True, "contract": contract_dict}


@router.delete("/contracts/{contract_id}", summary="Delete a contract")
def delete_contract_endpoint(
    contract_id: int,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Delete / deactivate a customer contract (admin only)."""
    username = _.get("username", "admin") if isinstance(_, dict) else "admin"
    ok = contract_repo.delete_contract(db, contract_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato no encontrado.")

    audit_repo.log_action(
        db=db,
        username=username,
        action="DELETE_CONTRACT",
        status="SUCCESS",
        details=f"Contrato ID {contract_id} eliminado exitosamente."
    )
    return {"success": True, "message": "Contrato eliminado correctamente."}


@router.post("/instances", summary="Create a new instance for a contract")
def create_instance(
    req: InstanceCreateRequest,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Register and store an encrypted database instance (admin only)."""
    username = _.get("username", "admin") if isinstance(_, dict) else "admin"
    instance = contract_repo.add_instance(db, req.contract_id, req.name, req.conn_str)
    audit_repo.log_action(
        db=db,
        username=username,
        action="CREATE_INSTANCE",
        instance_name=req.name,
        status="SUCCESS",
        details=f"Instancia '{req.name}' vinculada al contrato ID {req.contract_id}."
    )
    return {
        "success": True,
        "instance": {
            "id": instance.id,
            "name": instance.name
        }
    }


@router.post("/instances/{instance_id}/test", summary="Test connection to registered instance")
def test_instance_endpoint(
    instance_id: int,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(role_required(["Administrador", "DBA Principal"]))
):
    """Test remote connectivity and latency to an existing registered instance."""
    from app.models.contract import Instance
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instancia no encontrada.")

    return test_remote_connection(instance.conn_str)


@router.post("/instances/test-connection", summary="Test connection string on-the-fly")
def test_connection_string_endpoint(
    body: Dict[str, str],
    _: Dict[str, Any] = Depends(role_required(["Administrador", "DBA Principal"]))
):
    """Test connection string parameters before saving a new instance."""
    conn_str = body.get("conn_str")
    if not conn_str or not conn_str.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cadena de conexión requerida.")

    return test_remote_connection(conn_str.strip())



@router.get("/audit-logs", summary="Get system audit logs")
def list_audit_logs(
    action: str = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve audit logs of critical actions (cancellations, creation of contracts/instances, etc)."""
    return audit_repo.get_audit_logs(db, limit=limit, action=action)


@router.get("/system/maintenance", summary="Get global maintenance mode status")
def get_system_maintenance(
    _: Dict[str, Any] = Depends(get_current_user)
):
    """Returns current maintenance status for all authenticated users."""
    return maintenance_service.get_maintenance_status()


@router.post("/system/maintenance", summary="Toggle global maintenance mode (admin only)")
def set_system_maintenance(
    req: MaintenanceStatusRequest,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Toggle maintenance mode on or off. When active, non-admin users cannot dismiss overlay."""
    admin_username = _.get("username", "admin") if isinstance(_, dict) else "admin"

    status_dict = maintenance_service.set_maintenance_status(
        is_active=req.is_active,
        title=req.title,
        subtitle=req.subtitle,
        activated_by=admin_username,
        disabled_modules=req.disabled_modules
    )

    action_label = "SYSTEM_MAINTENANCE_ACTIVATED" if req.is_active else "SYSTEM_MAINTENANCE_DEACTIVATED"
    audit_repo.log_action(
        db=db,
        username=admin_username,
        action=action_label,
        status="SUCCESS",
        details=f"Modo mantenimiento {'activado' if req.is_active else 'desactivado'} por el admin."
    )

    return {
        "success": True,
        "maintenance": status_dict
    }


# ==============================================================================
# INCIDENT & REQUIREMENT MANAGEMENT (NO TOUCH DB DIRECTLY)
# ==============================================================================

@router.get("/incidents", response_model=IncidentListResponse, summary="List incidents and requirements with metrics")
def list_incidents(
    status: Optional[str] = None,
    ticket_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Retrieve all tickets, incidents, and requirements for administrative handling."""
    tickets = feedback_repo.get_all_tickets(
        db=db,
        status=status,
        ticket_type=ticket_type,
        search=search,
        limit=limit
    )
    stats = feedback_repo.get_ticket_stats(db=db)
    return {
        "incidents": tickets,
        "stats": stats
    }


@router.post("/incidents", response_model=IncidentResponse, summary="Create a new incident or requirement")
def create_incident(
    req: IncidentCreateRequest,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Create a new incident/requirement directly from the admin interface without touching the database."""
    admin_username = _.get("username", "admin") if isinstance(_, dict) else "admin"
    target_username = req.username or admin_username

    ticket = feedback_repo.create_ticket(
        db=db,
        username=target_username,
        ticket_type=req.ticket_type,
        module=req.module,
        priority=req.priority,
        description=req.description,
        status=req.status or "Abierto",
        notes=req.notes or ""
    )

    audit_repo.log_action(
        db=db,
        username=admin_username,
        action="CREATE_INCIDENT_TICKET",
        status="SUCCESS",
        details=f"Ticket #{ticket['id']} creado ({req.ticket_type} - {req.module} - {req.priority}) para {target_username}."
    )

    return ticket


@router.put("/incidents/{incident_id}", response_model=IncidentResponse, summary="Update status and notes of incident")
def update_incident(
    incident_id: int,
    req: IncidentUpdateRequest,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Update ticket resolution notes, status, priority, or details without direct DB access."""
    admin_username = _.get("username", "admin") if isinstance(_, dict) else "admin"

    updated = feedback_repo.update_ticket(
        db=db,
        ticket_id=incident_id,
        status=req.status,
        notes=req.notes,
        ticket_type=req.ticket_type,
        module=req.module,
        priority=req.priority,
        description=req.description
    )

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket o incidente no encontrado.")

    audit_repo.log_action(
        db=db,
        username=admin_username,
        action="UPDATE_INCIDENT_TICKET",
        status="SUCCESS",
        details=f"Ticket #{incident_id} actualizado. Estado: '{updated['status']}'. Notas: '{updated['notes'][:60] if updated['notes'] else ''}'."
    )

    return updated


@router.delete("/incidents/{incident_id}", summary="Delete an incident or requirement ticket")
def delete_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Delete an incident or requirement ticket (admin only)."""
    admin_username = _.get("username", "admin") if isinstance(_, dict) else "admin"
    ok = feedback_repo.delete_ticket(db, incident_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado.")

    audit_repo.log_action(
        db=db,
        username=admin_username,
        action="DELETE_INCIDENT_TICKET",
        status="SUCCESS",
        details=f"Ticket #{incident_id} eliminado del sistema por el administrador."
    )

    return {"success": True, "message": f"Ticket #{incident_id} eliminado exitosamente."}


class ResendInvitationRequest(BaseModel):
    new_password: Optional[str] = None


class TestEmailRequest(BaseModel):
    to_email: str


@router.get("/system/smtp-status", summary="Get SMTP email configuration status")
def get_smtp_status(
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Returns current SMTP connection settings and readiness."""
    return email_service.check_smtp_status()


@router.post("/system/test-email", summary="Send a test email via SMTP")
def send_test_email(
    req: TestEmailRequest,
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Sends a verification test email to validate SMTP configuration."""
    res = email_service.send_user_invitation(
        to_email=req.to_email,
        username="test_admin",
        full_name="Usuario de Prueba",
        password="TestPassword123!",
        role="Administrador"
    )
    return res


@router.post("/users/{user_id}/resend-invitation", summary="Resend user credential email")
def resend_user_invitation_endpoint(
    user_id: int,
    req: Optional[ResendInvitationRequest] = None,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(role_required("Administrador"))
):
    """Resend onboarding credentials email to a user, optionally setting a new password."""
    admin_username = _.get("username", "admin") if isinstance(_, dict) else "admin"
    user = user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario no tiene una dirección de correo registrada."
        )

    raw_password = (req.new_password.strip() if req and req.new_password and req.new_password.strip() else "DataCheck2026!*")
    hashed = get_password_hash(raw_password)
    user_repo.update_user_password(db, user.id, hashed)

    invitation = email_service.send_user_invitation(
        to_email=user.email.strip(),
        username=user.username,
        full_name=user.full_name or user.username,
        password=raw_password,
        role=user.role,
        unsubscribe_url=f"{settings.PUBLIC_API_URL}/auth/unsubscribe?token={create_unsubscribe_token(user.username)}"
    )

    audit_repo.log_action(
        db=db,
        username=admin_username,
        action="RESEND_USER_INVITATION",
        status="SUCCESS" if invitation.get("sent") else "WARNING",
        details=f"Invitación reenviada para '{user.username}' a '{user.email}'. Resultado: {invitation.get('method')} ({invitation.get('detail')})."
    )

    return {
        "success": invitation.get("sent", False),
        "message": "Invitación enviada exitosamente." if invitation.get("sent") else invitation.get("detail"),
        "invitation": invitation,
        "temporary_password": raw_password
    }



