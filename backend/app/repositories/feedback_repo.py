"""Feedback and Incident Repository."""
import re
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.feedback import Feedback
from app.models.user import User


def parse_ticket_comment(raw_comment: Optional[str]) -> Tuple[str, str, str, str]:
    """Extract (ticket_type, module, priority, clean_description) from comment string.
    
    Supports:
    - [Tipo - Modulo - Prioridad] Descripción
    - [Tipo - Modulo] Descripción
    - Plain description text
    """
    if not raw_comment:
        return "Incidente", "General", "Media", ""

    raw_str = raw_comment.strip()
    # Try 3-part: [Tipo - Modulo - Prioridad] Descripcion
    m3 = re.match(r"^\[\s*([^\]\-]+?)\s*-\s*([^\]\-]+?)\s*-\s*([^\]\-]+?)\s*\]\s*(.*)$", raw_str, re.DOTALL)
    if m3:
        return m3.group(1).strip(), m3.group(2).strip(), m3.group(3).strip(), m3.group(4).strip()

    # Try 2-part: [Tipo - Modulo] Descripcion
    m2 = re.match(r"^\[\s*([^\]\-]+?)\s*-\s*([^\]\-]+?)\s*\]\s*(.*)$", raw_str, re.DOTALL)
    if m2:
        return m2.group(1).strip(), m2.group(2).strip(), "Media", m2.group(3).strip()

    # Plain text fallback
    # Auto-detect if user wrote "requerimiento" or "incidente" in text
    lower = raw_str.lower()
    t_type = "Requerimiento" if "requerimiento" in lower or "solicitud" in lower else "Incidente"
    return t_type, "General", "Media", raw_str


def format_ticket_dict(fb: Feedback) -> Dict[str, Any]:
    """Format Feedback model into structured incident/requirement response."""
    t_type, module, prio, desc = parse_ticket_comment(fb.comment)
    username = fb.user.username if fb.user else f"user_{fb.user_id}"
    user_full_name = fb.user.full_name if fb.user else username
    user_email = fb.user.email if fb.user else None

    return {
        "id": fb.id,
        "user_id": fb.user_id,
        "username": username,
        "user_full_name": user_full_name,
        "user_email": user_email,
        "rating": fb.rating,
        "comment": fb.comment,
        "ticket_type": t_type,
        "module": module,
        "priority": prio,
        "description": desc or fb.comment or "",
        "status": fb.status or "Abierto",
        "notes": fb.notes or "",
        "created_at": fb.created_at.isoformat() if fb.created_at else None
    }


def add_feedback(db: Session, username: str, rating: int, comment: Optional[str] = None) -> int:
    """Store feedback or support ticket for user."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise ValueError("Usuario no encontrado")

    fb = Feedback(user_id=user.id, rating=rating, comment=comment)
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb.id


def get_feedback_by_id(db: Session, feedback_id: int) -> Optional[Feedback]:
    """Retrieve feedback/ticket by ID."""
    return db.query(Feedback).filter(Feedback.id == feedback_id).first()


def get_all_tickets(
    db: Session,
    status: Optional[str] = None,
    ticket_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 200
) -> List[Dict[str, Any]]:
    """Retrieve all support tickets/incidents with optional filtering."""
    query = db.query(Feedback).order_by(Feedback.id.desc())

    if status and status.strip() and status.lower() != "todos":
        query = query.filter(Feedback.status == status.strip())

    items = query.limit(limit).all()
    results = []

    search_term = search.strip().lower() if search else ""
    type_term = ticket_type.strip().lower() if ticket_type and ticket_type.lower() != "todos" else ""

    for fb in items:
        data = format_ticket_dict(fb)
        if type_term and data["ticket_type"].lower() != type_term:
            continue
        if search_term:
            match = (
                search_term in str(data["id"]) or
                search_term in data["username"].lower() or
                search_term in (data["user_full_name"] or "").lower() or
                search_term in data["description"].lower() or
                search_term in data["module"].lower() or
                search_term in (data["notes"] or "").lower()
            )
            if not match:
                continue
        results.append(data)

    return results


def get_ticket_stats(db: Session) -> Dict[str, int]:
    """Calculate aggregate ticket metrics."""
    all_fbs = db.query(Feedback).all()
    total = len(all_fbs)
    open_cnt = 0
    in_progress_cnt = 0
    resolved_cnt = 0
    closed_cnt = 0
    incidents_count = 0
    requirements_count = 0

    for fb in all_fbs:
        st = (fb.status or "").strip().lower()
        if st in {"abierto", "open", ""}:
            open_cnt += 1
        elif st in {"en progreso", "en_progreso", "in_progress", "asignado"}:
            in_progress_cnt += 1
        elif st in {"resuelto", "resolved"}:
            resolved_cnt += 1
        elif st in {"cerrado", "closed"}:
            closed_cnt += 1

        t_type, _, _, _ = parse_ticket_comment(fb.comment)
        if t_type.lower() == "requerimiento":
            requirements_count += 1
        else:
            incidents_count += 1

    return {
        "total": total,
        "open": open_cnt,
        "in_progress": in_progress_cnt,
        "resolved": resolved_cnt,
        "closed": closed_cnt,
        "incidents_count": incidents_count,
        "requirements_count": requirements_count
    }


def create_ticket(
    db: Session,
    username: str,
    ticket_type: str,
    module: str,
    priority: str,
    description: str,
    status: str = "Abierto",
    notes: str = ""
) -> Dict[str, Any]:
    """Create a structured incident/requirement ticket."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        # Fallback to first admin
        user = db.query(User).first()
    user_id = user.id if user else 1

    formatted_comment = f"[{ticket_type} - {module} - {priority}] {description}"
    fb = Feedback(
        user_id=user_id,
        rating=0,
        comment=formatted_comment,
        status=status,
        notes=notes
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return format_ticket_dict(fb)


def update_ticket(
    db: Session,
    ticket_id: int,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    ticket_type: Optional[str] = None,
    module: Optional[str] = None,
    priority: Optional[str] = None,
    description: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Update status, notes, or details of an existing ticket."""
    fb = db.query(Feedback).filter(Feedback.id == ticket_id).first()
    if not fb:
        return None

    if status is not None:
        fb.status = status
    if notes is not None:
        fb.notes = notes

    # If attributes of comment are edited
    curr_type, curr_module, curr_prio, curr_desc = parse_ticket_comment(fb.comment)
    new_type = ticket_type or curr_type
    new_module = module or curr_module
    new_prio = priority or curr_prio
    new_desc = description if description is not None else curr_desc

    if ticket_type or module or priority or description:
        fb.comment = f"[{new_type} - {new_module} - {new_prio}] {new_desc}"

    db.commit()
    db.refresh(fb)
    return format_ticket_dict(fb)


def delete_ticket(db: Session, ticket_id: int) -> bool:
    """Delete ticket by ID."""
    fb = db.query(Feedback).filter(Feedback.id == ticket_id).first()
    if not fb:
        return False
    db.delete(fb)
    db.commit()
    return True
