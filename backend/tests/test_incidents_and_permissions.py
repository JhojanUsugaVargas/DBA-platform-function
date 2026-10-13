"""Tests for DBA Principal Cancel Query Permissions and Incident Management Portal."""
import os
import unittest

os.environ["SECRET_KEY"] = "test-secret-key-12345"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DB_SCHEMA"] = ""

from app.db.session import SessionLocal, engine
from app.db.init_db import create_tables
from app.models import User, Feedback
from app.core.security import get_password_hash
from app.repositories import user_repo, feedback_repo
from app.api.chat import _can_kill_sessions, _handle_kill
from app.schemas.dba import CancelSessionRequest
from app.schemas.admin import IncidentCreateRequest, IncidentUpdateRequest
from app.api.admin import list_incidents, create_incident, update_incident, delete_incident
from app.api.dba import action_cancelar


class TestIncidentsAndPermissions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        create_tables()

    def setUp(self):
        self.db = SessionLocal()
        # Seed test users: Admin, DBA Principal, and Monitor
        self.admin_user = user_repo.create_user(
            db=self.db,
            username="admin_qa",
            full_name="Admin QA",
            hashed_password=get_password_hash("AdminPass123!"),
            role="Administrador"
        )
        self.dba_user = user_repo.create_user(
            db=self.db,
            username="dba_lead",
            full_name="Lead DBA",
            hashed_password=get_password_hash("DbaPass123!"),
            role="DBA Principal"
        )
        self.monitor_user = user_repo.create_user(
            db=self.db,
            username="monitor_qa",
            full_name="Monitor QA",
            hashed_password=get_password_hash("MonitorPass123!"),
            role="Monitor"
        )

    def tearDown(self):
        self.db.query(Feedback).delete()
        self.db.query(User).filter(User.username.in_(["admin_qa", "dba_lead", "monitor_qa"])).delete()
        self.db.commit()
        self.db.close()

    # -------------------------------------------------------------------------
    # 1. KILL / CANCEL QUERY PERMISSIONS TESTS
    # -------------------------------------------------------------------------
    def test_can_kill_sessions_helper(self):
        """Verify _can_kill_sessions allows Admin and DBA Principal, blocks Monitor."""
        self.assertTrue(_can_kill_sessions(self.db, "admin_qa"))
        self.assertTrue(_can_kill_sessions(self.db, "dba_lead"))
        self.assertFalse(_can_kill_sessions(self.db, "monitor_qa"))
        self.assertFalse(_can_kill_sessions(self.db, "non_existent_user"))

    def test_chat_kill_monitor_blocked(self):
        """Verify Monitor receives denial message when attempting to kill SPID via chat."""
        res = _handle_kill(self.db, "monitor_qa", 105)
        self.assertIn("Solo el Administrador y el DBA Principal", res)

    def test_dba_cancel_endpoint_validation(self):
        """Verify action_cancelar SPID validation works with DBA Principal identity."""
        req_invalid = CancelSessionRequest(spid="abc")
        dba_identity = {"username": "dba_lead", "role": "DBA Principal"}
        res = action_cancelar(body=req_invalid, _=dba_identity, user=dba_identity, db=self.db)
        self.assertEqual(res.get("type"), "error")
        self.assertIn("número entero válido", res.get("message"))

    # -------------------------------------------------------------------------
    # 2. INCIDENT & REQUIREMENT MANAGEMENT TESTS (WITHOUT TOUCHING DB DIRECTLY)
    # -------------------------------------------------------------------------
    def test_create_incident_via_admin_api(self):
        """Admin creates incident ticket via admin API without direct DB manipulation."""
        admin_ctx = {"username": "admin_qa", "role": "Administrador"}
        req = IncidentCreateRequest(
            ticket_type="Incidente",
            module="Base de Datos",
            priority="Alta",
            description="Consumo de CPU crítico en instancia de producción",
            status="Abierto",
            notes="Esperando reporte de telemetría"
        )
        ticket = create_incident(req=req, db=self.db, _=admin_ctx)
        self.assertIsNotNone(ticket.get("id"))
        self.assertEqual(ticket.get("ticket_type"), "Incidente")
        self.assertEqual(ticket.get("module"), "Base de Datos")
        self.assertEqual(ticket.get("priority"), "Alta")
        self.assertEqual(ticket.get("status"), "Abierto")
        self.assertIn("CPU crítico", ticket.get("description"))

    def test_create_requirement_via_admin_api(self):
        """Admin creates requirement ticket via admin API."""
        admin_ctx = {"username": "admin_qa", "role": "Administrador"}
        req = IncidentCreateRequest(
            ticket_type="Requerimiento",
            module="Seguridad",
            priority="Media",
            description="Crear cuenta para auditor externo con permisos de lectura",
            status="Abierto"
        )
        ticket = create_incident(req=req, db=self.db, _=admin_ctx)
        self.assertEqual(ticket.get("ticket_type"), "Requerimiento")
        self.assertEqual(ticket.get("priority"), "Media")

    def test_list_incidents_with_metrics(self):
        """Admin lists incidents and receives metrics and filtered results."""
        admin_ctx = {"username": "admin_qa", "role": "Administrador"}
        # Create 2 tickets
        feedback_repo.create_ticket(
            db=self.db,
            username="admin_qa",
            ticket_type="Incidente",
            module="Disco",
            priority="Crítica",
            description="Disco LUN casi lleno",
            status="Abierto"
        )
        feedback_repo.create_ticket(
            db=self.db,
            username="dba_lead",
            ticket_type="Requerimiento",
            module="Backup",
            priority="Baja",
            description="Ajustar ventana de copia a las 23:00",
            status="Resuelto"
        )

        res = list_incidents(db=self.db, _=admin_ctx)
        incidents = res["incidents"]
        stats = res["stats"]

        self.assertGreaterEqual(len(incidents), 2)
        self.assertGreaterEqual(stats["total"], 2)
        self.assertGreaterEqual(stats["incidents_count"], 1)
        self.assertGreaterEqual(stats["requirements_count"], 1)

    def test_update_incident_status_and_notes(self):
        """Admin resolves ticket and adds agent notes without touching the DB directly."""
        admin_ctx = {"username": "admin_qa", "role": "Administrador"}
        ticket = feedback_repo.create_ticket(
            db=self.db,
            username="dba_lead",
            ticket_type="Incidente",
            module="Memoria",
            priority="Alta",
            description="Error Out of Memory en buffer pool",
            status="Abierto"
        )

        update_req = IncidentUpdateRequest(
            status="Resuelto",
            notes="Se aumentó el max server memory a 64GB y se reinició la instancia."
        )
        updated = update_incident(incident_id=ticket["id"], req=update_req, db=self.db, _=admin_ctx)

        self.assertEqual(updated["status"], "Resuelto")
        self.assertIn("64GB", updated["notes"])

    def test_delete_incident_via_admin_api(self):
        """Admin deletes an incident ticket without touching DB directly."""
        admin_ctx = {"username": "admin_qa", "role": "Administrador"}
        ticket = feedback_repo.create_ticket(
            db=self.db,
            username="admin_qa",
            ticket_type="Incidente",
            module="Test",
            priority="Baja",
            description="Ticket temporal para borrar",
            status="Abierto"
        )

        del_res = delete_incident(incident_id=ticket["id"], db=self.db, _=admin_ctx)
        self.assertTrue(del_res["success"])

        # Verify it's gone
        found = feedback_repo.get_feedback_by_id(self.db, ticket["id"])
        self.assertIsNone(found)

    # -------------------------------------------------------------------------
    # 3. INSTANCE HEALTHCHECK & BACKUP MONITORING TESTS
    # -------------------------------------------------------------------------
    def test_remote_connection_invalid_fails_safely(self):
        """Testing invalid connection string returns structured failure without crashing."""
        from app.services.remote_db_service import test_remote_connection
        res = test_remote_connection("invalid_connection_string_test")
        self.assertFalse(res["success"])
        self.assertIn("error", res)
        self.assertIsInstance(res["latency_ms"], (int, float))

    def test_backup_status_parser_sqlserver(self):
        """Verify get_backup_status parses rows and flags critical/warning correctly."""
        from unittest.mock import MagicMock
        from app.services.remote_db_service import get_backup_status

        mock_cursor = MagicMock()
        mock_cursor.description = [
            ("database_name",), ("recovery_model",), ("last_full_backup",),
            ("hours_since_full",), ("last_diff_backup",), ("last_log_backup",)
        ]
        # Database 1: recent backup (healthy)
        # Database 2: no backup (critical)
        # Database 3: backup > 24 hours (critical)
        mock_cursor.fetchall.return_value = [
            ("ProdDB", "FULL", "2026-10-13 02:00:00", "Nunca", "2026-10-13 07:00:00", 5),
            ("BillingDB", "SIMPLE", None, None, None, None),
            ("LegacyDB", "FULL", "2026-10-10 01:00:00", None, None, 72),
        ]

        result = get_backup_status(mock_cursor, "sqlserver")
        self.assertEqual(result["engine"], "SQL Server")
        self.assertEqual(result["total_databases"], 3)
        self.assertEqual(result["critical_count"], 2)  # BillingDB (Nunca) + LegacyDB (>24h)
        self.assertEqual(len(result["databases"]), 3)
        self.assertEqual(result["databases"][0]["status"], "OK")
        self.assertEqual(result["databases"][1]["status"], "CRITICAL")
        self.assertEqual(result["databases"][2]["status"], "CRITICAL")


if __name__ == "__main__":
    unittest.main()

