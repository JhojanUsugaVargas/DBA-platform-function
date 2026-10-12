"""Interactive Chat and Assistant Endpoints."""
import re
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, ADMIN_ROLES
from app.db.session import get_db
from app.repositories import chat_repo, user_repo
from app.schemas.chat import ChatRequest, ChatResponse, ChatMessageResponse
from app.services.ai_service import get_ai_response
from app.services.ticket_service import action_soporte
from app.services.remote_db_service import (
    NoInstanceSelected,
    remote_cursor,
    kill_session
)

router = APIRouter()

KILL_PATTERN = re.compile(r"\b(matar|kill|desconectar|terminar)\b\D*?(\d{1,10})\b", re.IGNORECASE)


def _is_admin(db: Session, username: str) -> bool:
    user = user_repo.get_by_username(db, username)
    return bool(user and (user.role or "").strip().lower() in ADMIN_ROLES)


def _handle_kill(db: Session, username: str, spid: int) -> str:
    if not _is_admin(db, username):
        return "⛔ Solo los administradores pueden terminar sesiones."
    try:
        with remote_cursor(username) as (cursor, engine):
            kill_session(cursor, engine, spid)
        return (
            f"✅ ¡Comando ejecutado! Se solicitó terminar la sesión/proceso {spid} "
            f"en el motor {engine.upper()}."
        )
    except NoInstanceSelected:
        return "⚠️ Selecciona primero una instancia para poder terminar la sesión."
    except Exception as exc:
        logging.exception("Error al terminar la sesión %s", spid)
        return (
            f"❌ Error al intentar terminar la sesión {spid}. "
            f"Revisa que exista y tengas permisos. Detalles: {exc}"
        )


@router.get("/history", response_model=List[ChatMessageResponse], summary="Get chat history for user")
def chat_history(
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve chat history messages."""
    return chat_repo.get_chat_history(db)


@router.post("/message", response_model=ChatResponse, summary="Send message to DataCheck Assistant")
def post_message(
    req: ChatRequest,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Handle conversational AI, ticket generation or database kill actions."""
    username = user["username"]
    message = req.message.strip()
    lowered = message.lower()

    # Save user message
    chat_repo.add_chat_message(db, username, message)

    options = None
    if lowered.startswith("soporte") and len(lowered) > len("soporte"):
        detail = message[len("soporte"):].strip()
        tipo_ticket = "Soporte chat"
        for t in ["Requerimiento", "Incidente", "Consulta", "Seguimiento"]:
            if detail.lower().startswith(t.lower()):
                tipo_ticket = t
                detail = detail[len(t):].lstrip(":").strip()
                break

        reply = action_soporte(
            {"mensaje": detail, "tipo": tipo_ticket, "modulo": "Chat"},
            user
        ).get("message", "Ticket procesado.")

    elif lowered == "soporte":
        reply = "📝 **Centro de Soporte**\n¿Qué tipo de solicitud deseas reportar?"
        options = [
            "soporte Requerimiento: ",
            "soporte Incidente: ",
            "soporte Consulta: ",
            "soporte Seguimiento: #"
        ]

    elif (kill := KILL_PATTERN.search(message)):
        reply = _handle_kill(db, username, int(kill.group(2)))

    else:
        ai_res = get_ai_response(message, username)
        reply = ai_res.get("message", "Sin respuesta del asistente.")

    # Save bot message
    chat_repo.add_chat_message(db, "AI_DBA", reply)

    return ChatResponse(reply=reply, options=options)
