"""Support ticket tracking service."""
import re
import logging
from typing import Dict, Any
from app.db.session import SessionLocal
from app.models.feedback import Feedback
from app.models.user import User


def action_soporte(data: Dict[str, Any], current_user: Dict[str, Any]) -> Dict[str, Any]:
    """Registra y consulta tickets de soporte estructurados."""
    if not data or not isinstance(data, dict):
        return {
            "type": "prompt",
            "message": "📝 Por favor describe tu solicitud de soporte:",
            "input_action": "soporte"
        }

    mensaje = data.get("mensaje")
    if not mensaje:
        return {"type": "error", "message": "❌ El mensaje es obligatorio."}

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == current_user["username"]).first()
        user_id = user.id if user else 1

        tipo = data.get("tipo", "Incidente")
        modulo = data.get("modulo", "General")

        if tipo == "Seguimiento":
            match = re.search(r"\d+", mensaje)
            if not match:
                return {
                    "type": "error",
                    "message": "❌ Por favor indica el número de ticket válido (ejemplo: #5)."
                }
            ticket_id = int(match.group())

            ticket = db.query(Feedback).filter(Feedback.id == ticket_id).first()
            if not ticket:
                return {
                    "type": "error",
                    "message": f"❌ No se encontró el ticket #{ticket_id}."
                }

            notas = ticket.notes.strip() if ticket.notes else "Aún no hay notas del agente."
            estado_icono = "🟢" if ticket.status == "Resuelto" else "⏳"
            return {
                "type": "info",
                "message": (
                    f"📋 **Seguimiento del Ticket #{ticket_id}**\n\n"
                    f"{estado_icono} **Estado:** {ticket.status}\n\n"
                    f"📝 **Notas del Agente:**\n{notas}\n\n"
                    f"💬 **Descripción original:**\n_{ticket.comment}_"
                )
            }

        # Guardar en la tabla Feedback con rating=0 indicando ticket de soporte
        nuevo_ticket = Feedback(
            user_id=user_id,
            rating=0,
            comment=f"[{tipo} - {modulo}] {mensaje}"
        )
        db.add(nuevo_ticket)
        db.commit()
        db.refresh(nuevo_ticket)
        ticket_id = nuevo_ticket.id

        return {
            "type": "success",
            "message": (
                f"✅ **¡Ticket #{ticket_id} registrado exitosamente!**\n"
                f"⏱️ **Tiempo estimado de resolución:** 4 horas.\n"
                f"Nos pondremos en contacto pronto."
            )
        }
    except Exception as exc:
        db.rollback()
        logging.error(f"Error registrando soporte: {exc}")
        return {"type": "error", "message": f"❌ Error al registrar soporte: {str(exc)}"}
    finally:
        db.close()
