"""Support ticket tracking service."""
import re
import logging
from typing import Dict, Any
from app.db.session import SessionLocal
from app.models.feedback import Feedback
from app.models.user import User


from app.repositories.feedback_repo import parse_ticket_comment


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
                    "message": "❌ Por favor indica el número de ticket válido (ejemplo: #1 o soporte Seguimiento: #1)."
                }
            ticket_id = int(match.group())

            ticket = db.query(Feedback).filter(Feedback.id == ticket_id).first()
            if not ticket:
                return {
                    "type": "error",
                    "message": f"❌ No se encontró el ticket #{ticket_id} en el sistema."
                }

            # Extraer componentes limpios del comentario
            t_type, mod, prio, clean_desc = parse_ticket_comment(ticket.comment)

            # Badges de estado
            status_map = {
                "Resuelto": "🟢 Resuelto",
                "En Progreso": "🟡 En Progreso",
                "Abierto": "🔵 Abierto",
                "Cerrado": "⚪ Cerrado"
            }
            estado_badge = status_map.get(ticket.status, f"⚪ {ticket.status or 'Abierto'}")

            # Badges de prioridad
            prio_map = {
                "Crítica": "🔴 Crítica",
                "Critica": "🔴 Crítica",
                "Alta": "🟠 Alta",
                "Media": "🟡 Media",
                "Baja": "🟢 Baja"
            }
            prio_badge = prio_map.get(prio, f"⚡ {prio}")

            # Metadatos del ticket
            fecha_str = ticket.created_at.strftime("%d/%m/%Y %I:%M %p") if ticket.created_at else "No registrada"
            solicitante = ticket.user.username if (ticket.user and ticket.user.username) else f"Usuario #{ticket.user_id}"

            # Notas del agente
            if ticket.notes and ticket.notes.strip():
                notas = ticket.notes.strip()
            else:
                notas = "El ticket se encuentra en cola de atención. Aún no cuenta con notas del agente."

            # Descripción limpia (sin prefijos técnicos de corchetes)
            desc_text = clean_desc if clean_desc else (ticket.comment or "Sin descripción registrada.")

            card_message = (
                f"📋 **FICHA DE SEGUIMIENTO • TICKET #{ticket_id}**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• **Estado:** {estado_badge}\n"
                f"• **Tipo:** {t_type} | **Módulo:** {mod}\n"
                f"• **Prioridad:** {prio_badge}\n"
                f"• **Fecha de registro:** 📅 {fecha_str}\n"
                f"• **Solicitante:** 👤 {solicitante}\n\n"
                f"📝 **Notas del Agente / Resolución:**\n"
                f"> {notas}\n\n"
                f"💬 **Descripción reportada:**\n"
                f"> {desc_text}"
            )

            return {
                "type": "info",
                "message": card_message
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
                f"✅ **¡Ticket #{ticket_id} registrado exitosamente!**\n\n"
                f"• **Tipo:** {tipo}\n"
                f"• **Módulo:** {modulo}\n"
                f"• **Estado inicial:** 🔵 Abierto\n"
                f"⏱️ **Tiempo estimado de atención:** 2 a 4 horas.\n\n"
                f"💡 _Para consultar el avance escribe:_ `soporte Seguimiento: #{ticket_id}`"
            )
        }
    except Exception as exc:
        db.rollback()
        logging.error(f"Error registrando soporte: {exc}")
        return {"type": "error", "message": f"❌ Error al registrar soporte: {str(exc)}"}
    finally:
        db.close()

