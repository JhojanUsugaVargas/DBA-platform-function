"""Global System Maintenance Mode Service.

Manages persistent database maintenance status with role-based lockouts and in-memory caching.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.db.session import SessionLocal

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
    """Return the current system maintenance status from DB or cache."""
    try:
        db = SessionLocal()
        try:
            from app.models.system_maintenance import SystemMaintenance
            row = db.query(SystemMaintenance).first()
            if row:
                _maintenance_state["is_active"] = bool(row.is_active)
                _maintenance_state["title"] = row.title or "Ajustes del Sistema en Progreso"
                _maintenance_state["subtitle"] = row.subtitle or ""
                _maintenance_state["activated_by"] = row.activated_by
                _maintenance_state["activated_at"] = row.activated_at.isoformat() if row.activated_at else None
                _maintenance_state["updated_at"] = row.updated_at.isoformat() if row.updated_at else None
                try:
                    _maintenance_state["disabled_modules"] = json.loads(row.disabled_modules or "[]")
                except Exception:
                    _maintenance_state["disabled_modules"] = []
        finally:
            db.close()
    except Exception as exc:
        logging.warning("No se pudo leer mantenimiento desde BD (usando caché): %s", exc)

    return dict(_maintenance_state)


def set_maintenance_status(
    is_active: bool,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    activated_by: str = "admin",
    disabled_modules: Optional[list] = None,
) -> Dict[str, Any]:
    """Update global or granular system maintenance status and persist to PostgreSQL."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    modules_list = disabled_modules if disabled_modules is not None else ([] if not is_active else _maintenance_state.get("disabled_modules", []))

    # Update in-memory
    _maintenance_state["is_active"] = is_active
    if is_active and not _maintenance_state.get("activated_at"):
        _maintenance_state["activated_at"] = now_iso
    elif not is_active:
        _maintenance_state["activated_at"] = None

    if title:
        _maintenance_state["title"] = title
    if subtitle:
        _maintenance_state["subtitle"] = subtitle
    _maintenance_state["activated_by"] = activated_by if is_active else None
    _maintenance_state["updated_at"] = now_iso
    _maintenance_state["disabled_modules"] = modules_list

    # Persist in DB
    try:
        db = SessionLocal()
        try:
            from app.models.system_maintenance import SystemMaintenance
            row = db.query(SystemMaintenance).first()
            if not row:
                row = SystemMaintenance(id=1)
                db.add(row)
            row.is_active = is_active
            if title:
                row.title = title
            if subtitle:
                row.subtitle = subtitle
            row.activated_by = activated_by if is_active else None
            row.activated_at = now if is_active else None
            row.updated_at = now
            row.disabled_modules = json.dumps(modules_list)
            db.commit()
            logging.info("Estado de mantenimiento persistido en base de datos PostgreSQL.")
        finally:
            db.close()
    except Exception as exc:
        logging.error("Error al persistir estado de mantenimiento en BD: %s", exc)

    return dict(_maintenance_state)
