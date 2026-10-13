"""Global System Maintenance Mode Service.

Manages persistent in-memory maintenance status with metadata and role-based lockouts.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional

_maintenance_state: Dict[str, Any] = {
    "is_active": False,
    "title": "Ajustes del Sistema en Progreso",
    "subtitle": "Optimizando motores de bases de datos, reindexando y aplicando configuraciones DBA...",
    "activated_by": None,
    "activated_at": None,
    "updated_at": None,
    "disabled_modules": [],
}


def get_maintenance_status() -> Dict[str, Any]:
    """Return the current system maintenance status."""
    return dict(_maintenance_state)


def set_maintenance_status(
    is_active: bool,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    activated_by: str = "admin",
    disabled_modules: Optional[list] = None,
) -> Dict[str, Any]:
    """Update global or granular system maintenance status."""
    now_iso = datetime.now(timezone.utc).isoformat()
    if is_active and not _maintenance_state.get("is_active"):
        _maintenance_state["activated_at"] = now_iso
    elif not is_active:
        _maintenance_state["activated_at"] = None

    _maintenance_state["is_active"] = is_active
    if title:
        _maintenance_state["title"] = title
    if subtitle:
        _maintenance_state["subtitle"] = subtitle
    _maintenance_state["activated_by"] = activated_by if is_active else None
    _maintenance_state["updated_at"] = now_iso
    _maintenance_state["disabled_modules"] = disabled_modules if disabled_modules is not None else ([] if not is_active else _maintenance_state.get("disabled_modules", []))
    return dict(_maintenance_state)
