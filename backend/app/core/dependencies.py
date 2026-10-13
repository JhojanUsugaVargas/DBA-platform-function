"""Authentication and Authorization FastAPI Dependencies."""
from typing import Dict, Any, Callable, Union, List, Set
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

ADMIN_ROLES = {"admin", "administrador"}


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Dependency to retrieve the authenticated user payload from Bearer token."""
    payload = decode_access_token(token)
    username: str = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de autenticación inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"username": username, "role": payload.get("role")}


def role_required(required_role: Union[str, List[str], Set[str]]) -> Callable:
    """Dependency factory to verify user has one of the required roles (or is admin)."""
    if isinstance(required_role, (list, tuple, set)):
        req_set = {r.strip().lower() for r in required_role if isinstance(r, str)}
    else:
        req_set = {required_role.strip().lower()}

    allowed = ADMIN_ROLES | req_set

    async def dependency(
        current_user: Dict[str, Any] = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        from app.db.session import SessionLocal
        session = db if isinstance(db, Session) else SessionLocal()
        try:
            user = session.query(User).filter(User.username == current_user["username"]).first()
            role = (user.role or "").strip().lower() if user else ""

            if role not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permisos insuficientes para realizar esta acción"
                )
            return current_user
        finally:
            if session is not db:
                session.close()

    return dependency

