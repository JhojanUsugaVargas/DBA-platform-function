"""Comprehensive QA Test Suite for DataCheck Platform.

Tests Core Security, Repositories, API Handlers, Error Handling, and Edge Cases.
"""
import os
import unittest
import asyncio
from datetime import timedelta

# Configure test environment
os.environ["SECRET_KEY"] = "qa-test-secret-key-987654321"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DB_SCHEMA"] = ""
os.environ["DEBUG"] = "false"

from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    encrypt_data,
    decrypt_data,
)
from app.core.dependencies import get_current_user, role_required
from app.db.session import SessionLocal, engine
from app.db.init_db import create_tables
from app.models import User, Contract, Instance, ChatMessage, Feedback, AuditLog
from app.repositories import user_repo, contract_repo, chat_repo, feedback_repo, audit_repo
from app.schemas.auth import TokenResponse, UserProfileResponse
from app.schemas.admin import (
    ContractCreateRequest,
    ContractUpdateRequest,
    InstanceCreateRequest,
    UserCreateRequest,
    UserUpdateRequest,
    UserChangePasswordRequest,
    MaintenanceStatusRequest
)
from app.schemas.dba import CancelSessionRequest, HistoricalCpuResponse
from app.schemas.chat import ChatRequest
from app.schemas.feedback import FeedbackSubmitRequest
from app.api.auth import login as api_login
from app.api.admin import (
    list_contracts,
    list_users,
    create_contract,
    update_contract_endpoint,
    delete_contract_endpoint,
    create_instance,
    list_audit_logs,
    create_user as admin_create_user,
    change_user_password_endpoint,
    update_user_endpoint,
    get_system_maintenance,
    set_system_maintenance
)
from app.api.chat import clear_chat_history_endpoint
from app.api.dba import (
    action_cancelar,
    action_status,
    action_cpu,
    action_discos,
    get_historical_cpu,
    action_bloqueos,
    action_waitstats,
    action_bloat,
    action_maintenance,
    get_telemetry_overview
)
from app.services.dba_queries import (
    query_blocking_chain,
    query_wait_stats,
    query_bloat_fragmentation,
    query_maintenance_stats
)
from app.services import ticket_service, ai_service, remote_db_service


class QATestSuite(unittest.TestCase):
    """Automated QA Test Suite covering all platform domains."""

    @classmethod
    def setUpClass(cls):
        create_tables()

    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    # --------------------------------------------------------------------------
    # 1. SECURITY & CRYPTOGRAPHY TESTS
    # --------------------------------------------------------------------------
    def test_sec_01_password_hashing_and_verification(self):
        """QA-SEC-01: Verify bcrypt password hashing correctness."""
        password = "P@ssw0rd_Super_Complex_2026!"
        hashed = get_password_hash(password)
        self.assertNotEqual(password, hashed)
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("WrongPassword123", hashed))
        self.assertFalse(verify_password("", hashed))

    def test_sec_02_jwt_token_generation_and_claims(self):
        """QA-SEC-02: Verify JWT token generation, payload decoding and expiration."""
        payload = {"sub": "qa_tester", "role": "SuperAdmin"}
        token = create_access_token(payload, expires_delta=timedelta(minutes=30))
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 20)

        decoded = decode_access_token(token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded.get("sub"), "qa_tester")
        self.assertEqual(decoded.get("role"), "SuperAdmin")
        self.assertIn("exp", decoded)

    def test_sec_03_jwt_malformed_token_rejection(self):
        """QA-SEC-03: Verify that malformed or forged tokens are safely rejected returning empty dict."""
        tampered_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
        decoded = decode_access_token(tampered_token)
        self.assertEqual(decoded, {})

    def test_sec_04_fernet_encryption_and_fallback(self):
        """QA-SEC-04: Verify Fernet symmetric encryption and graceful fallback for plaintext strings."""
        raw_conn = "MockServer=mock-sql.test.local;MockDatabase=master;MockUser=test_sa;MockToken=test_pass;"
        encrypted = encrypt_data(raw_conn)
        self.assertNotEqual(raw_conn, encrypted)

        decrypted = decrypt_data(encrypted)
        self.assertEqual(raw_conn, decrypted)

        # Fallback for unencrypted legacy string returns string as-is
        plaintext_fallback = decrypt_data("MockLegacyPlaintext")
        self.assertEqual(plaintext_fallback, "MockLegacyPlaintext")

    # --------------------------------------------------------------------------
    # 2. REPOSITORY & DATA INTEGRITY TESTS
    # --------------------------------------------------------------------------
    def test_data_01_user_lifecycle(self):
        """QA-DATA-01: Verify user creation, duplicate protection and lookup."""
        username = "qa_user_alpha"
        user = user_repo.create_user(
            db=self.db,
            username=username,
            full_name="QA Alpha Tester",
            hashed_password=get_password_hash("Pass123!"),
            role="Monitor"
        )
        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, username)

        found = user_repo.get_by_username(self.db, username)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, user.id)

        not_found = user_repo.get_by_username(self.db, "non_existent_ghost_user")
        self.assertIsNone(not_found)

    def test_data_02_contract_and_instance_cascade(self):
        """QA-DATA-02: Verify contract management and instance association."""
        contract = contract_repo.add_contract(self.db, "QA Enterprise Contract")
        contract_id = contract["id"]
        self.assertIsNotNone(contract_id)

        inst1 = contract_repo.add_instance(
            db=self.db,
            contract_id=contract_id,
            name="SRV-SQL-01",
            conn_str="MockHost=10.0.0.1;MockUser=dba_test;"
        )
        self.assertIsNotNone(inst1.id)

        inst2 = contract_repo.add_instance(
            db=self.db,
            contract_id=contract_id,
            name="SRV-SQL-02",
            conn_str="MockHost=10.0.0.2;MockUser=dba_test;"
        )
        self.assertIsNotNone(inst2.id)

        instances = contract_repo.get_instances_by_contract(self.db, contract_id)
        self.assertEqual(len(instances), 2)
        names = [i["name"] for i in instances]
        self.assertIn("SRV-SQL-01", names)
        self.assertIn("SRV-SQL-02", names)

    def test_data_03_chat_persistence_and_order(self):
        """QA-DATA-03: Verify chat messages persist and preserve chronological order."""
        user_repo.create_user(
            db=self.db,
            username="qa_chat_admin",
            full_name="Chat Admin",
            hashed_password=get_password_hash("Pass123!"),
            role="Administrador"
        )
        chat_repo.add_chat_message(self.db, "qa_chat_admin", "Mensaje 1: Inicio diagnostico")
        chat_repo.add_chat_message(self.db, "qa_chat_admin", "Respuesta 1: Sistema preparado")

        history = chat_repo.get_chat_history(self.db, limit=10)
        self.assertTrue(len(history) >= 2)
        contents = [m["content"] for m in history]
        self.assertIn("Mensaje 1: Inicio diagnostico", contents)
        self.assertIn("Respuesta 1: Sistema preparado", contents)

    def test_data_04_feedback_submission(self):
        """QA-DATA-04: Verify feedback submission and retrieval."""
        user_repo.create_user(
            db=self.db,
            username="qa_fb_user",
            full_name="Feedback Tester",
            hashed_password=get_password_hash("Pass123!"),
            role="Monitor"
        )
        fb = feedback_repo.add_feedback(
            db=self.db,
            username="qa_fb_user",
            rating=5,
            comment="Excelente plataforma de telemetria"
        )
        self.assertIsInstance(fb, int)
        self.assertTrue(fb > 0)
        saved = feedback_repo.get_feedback_by_id(self.db, fb)
        self.assertIsNotNone(saved)
        self.assertEqual(saved.rating, 5)
        self.assertEqual(saved.comment, "Excelente plataforma de telemetria")

    # --------------------------------------------------------------------------
    # 3. API ROUTER & AUTHENTICATION ENDPOINTS
    # --------------------------------------------------------------------------
    def test_api_01_login_success_and_failure(self):
        """QA-API-01: Verify login API handler with valid and invalid credentials."""
        user_repo.create_user(
            db=self.db,
            username="qa_auth_tester",
            full_name="Auth Tester",
            hashed_password=get_password_hash("CorrectPass123!"),
            role="Administrador"
        )

        # 1. Successful login
        form_ok = OAuth2PasswordRequestForm(
            grant_type="password",
            username="qa_auth_tester",
            password="CorrectPass123!",
            scope="",
            client_id=None,
            client_secret=None
        )
        res_ok = api_login(form_data=form_ok, db=self.db)
        self.assertIsInstance(res_ok, TokenResponse)
        self.assertEqual(res_ok.token_type, "bearer")
        self.assertFalse(res_ok.requires_mfa)
        self.assertTrue(len(res_ok.access_token) > 20)

        # 2. Invalid password -> 401
        form_bad_pwd = OAuth2PasswordRequestForm(
            grant_type="password",
            username="qa_auth_tester",
            password="WrongPassword!",
            scope="",
            client_id=None,
            client_secret=None
        )
        with self.assertRaises(HTTPException) as ctx:
            api_login(form_data=form_bad_pwd, db=self.db)
        self.assertEqual(ctx.exception.status_code, 401)

        # 3. Nonexistent user -> 401
        form_ghost = OAuth2PasswordRequestForm(
            grant_type="password",
            username="ghost_user_xyz",
            password="AnyPassword!",
            scope="",
            client_id=None,
            client_secret=None
        )
        with self.assertRaises(HTTPException) as ctx2:
            api_login(form_data=form_ghost, db=self.db)
        self.assertEqual(ctx2.exception.status_code, 401)

    def test_api_02_rbac_authorization_guard(self):
        """QA-API-02: Verify Role-Based Access Control decorator/guard."""
        checker = role_required("Administrador")

        user_repo.create_user(
            db=self.db,
            username="rbac_admin",
            full_name="RBAC Admin",
            hashed_password=get_password_hash("pass"),
            role="Administrador"
        )
        user_repo.create_user(
            db=self.db,
            username="rbac_monitor",
            full_name="RBAC Monitor",
            hashed_password=get_password_hash("pass"),
            role="Monitor"
        )

        # Admin user passes
        admin_user = {"id": 1, "username": "rbac_admin", "role": "Administrador"}
        res = asyncio.run(checker(current_user=admin_user, db=self.db))
        self.assertEqual(res["username"], "rbac_admin")

        # Monitor user is rejected with 403 Forbidden
        monitor_user = {"id": 2, "username": "rbac_monitor", "role": "Monitor"}
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(checker(current_user=monitor_user, db=self.db))
        self.assertEqual(ctx.exception.status_code, 403)

    def test_api_03_contract_creation_endpoint(self):
        """QA-API-03: Verify contract creation endpoint."""
        admin_user = {"id": 1, "username": "admin", "role": "Administrador"}
        payload = ContractCreateRequest(name="Contrato QA 2026")
        res = create_contract(req=payload, db=self.db, _=admin_user)
        self.assertTrue(res["success"])
        self.assertEqual(res["contract"]["name"], "Contrato QA 2026")

    def test_api_03b_contract_update_and_delete_endpoints(self):
        """QA-API-03b: Verify contract update and soft delete endpoints."""
        admin_user = {"id": 1, "username": "admin", "role": "Administrador"}
        c = create_contract(req=ContractCreateRequest(name="Contrato Temporal"), db=self.db, _=admin_user)
        cid = c["contract"]["id"]

        # Update
        up_res = update_contract_endpoint(
            contract_id=cid,
            req=ContractUpdateRequest(name="Contrato Modificado QA"),
            db=self.db,
            _=admin_user
        )
        self.assertTrue(up_res["success"])
        self.assertEqual(up_res["contract"]["name"], "Contrato Modificado QA")

        # Delete
        del_res = delete_contract_endpoint(contract_id=cid, db=self.db, _=admin_user)
        self.assertTrue(del_res["success"])

        # Check list doesn't include it
        active_list = list_contracts(db=self.db, _=admin_user)
        self.assertFalse(any(x["id"] == cid for x in active_list))

    def test_api_03c_user_password_and_email_invitation(self):
        """QA-API-03c: Verify user creation with custom password and admin password reset."""
        admin_user = {"id": 1, "username": "admin", "role": "Administrador"}
        create_res = admin_create_user(
            user_req=UserCreateRequest(
                username="qa_invited_user",
                full_name="Invited QA",
                email="qa_invited@example.com",
                password="CustomPass2026!",
                role="Monitor"
            ),
            db=self.db,
            _=admin_user
        )
        self.assertTrue(create_res["success"])
        self.assertIsNotNone(create_res["invitation"])
        uid = create_res["user"]["id"]

        # Admin reset password for other user
        pwd_res = change_user_password_endpoint(
            user_id=uid,
            req=UserChangePasswordRequest(new_password="NewAdminResetPass123!"),
            db=self.db,
            _=admin_user
        )
        self.assertTrue(pwd_res["success"])
        u = user_repo.get_by_id(self.db, uid)
        self.assertTrue(verify_password("NewAdminResetPass123!", u.hashed_password))

    def test_api_03d_update_user_details(self):
        """QA-API-03d: Verify admin can edit existing user full name, email, and role."""
        admin_user = {"id": 1, "username": "admin", "role": "Administrador"}
        u = user_repo.create_user(
            db=self.db,
            username="qa_editable_user",
            full_name="Original Name",
            hashed_password=get_password_hash("Pass123!"),
            role="Monitor",
            email="original@example.com"
        )
        res = update_user_endpoint(
            user_id=u.id,
            req=UserUpdateRequest(
                full_name="Updated Pro DBA",
                email="updated@example.com",
                role="DBA Principal"
            ),
            db=self.db,
            _=admin_user
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["user"]["full_name"], "Updated Pro DBA")
        self.assertEqual(res["user"]["email"], "updated@example.com")
        self.assertEqual(res["user"]["role"], "DBA Principal")

        refreshed = user_repo.get_by_id(self.db, u.id)
        self.assertEqual(refreshed.full_name, "Updated Pro DBA")
        self.assertEqual(refreshed.role, "DBA Principal")

    def test_api_03e_system_maintenance_mode(self):
        """QA-API-03e: Verify global maintenance mode toggle and non-admin restrictions."""
        admin_user = {"id": 1, "username": "admin", "role": "Administrador"}
        monitor_user = {"id": 2, "username": "monitor_user", "role": "Monitor"}

        # Activate maintenance
        act_res = set_system_maintenance(
            req=MaintenanceStatusRequest(is_active=True, title="Ajustes DBA", subtitle="Optimizando índices..."),
            db=self.db,
            _=admin_user
        )
        self.assertTrue(act_res["success"])
        self.assertTrue(act_res["maintenance"]["is_active"])

        # Check status as any authenticated user
        status_res = get_system_maintenance(_=monitor_user)
        self.assertTrue(status_res["is_active"])
        self.assertEqual(status_res["title"], "Ajustes DBA")

        # Deactivate maintenance
        deact_res = set_system_maintenance(
            req=MaintenanceStatusRequest(is_active=False),
            db=self.db,
            _=admin_user
        )
        self.assertTrue(deact_res["success"])
        self.assertFalse(deact_res["maintenance"]["is_active"])

    # --------------------------------------------------------------------------
    # 4. SERVICE LAYER & RESILIENCE TESTS
    # --------------------------------------------------------------------------
    def test_srv_01_ticket_service_syntax_and_formatting(self):
        """QA-SRV-01: Verify ticket service creation with structured message."""
        user_repo.create_user(
            db=self.db,
            username="qa_ticket_user",
            full_name="Ticket Tester",
            hashed_password=get_password_hash("Pass123!"),
            role="Monitor"
        )
        result = ticket_service.action_soporte(
            data={"mensaje": "Alerta: CPU Crítica > 95%", "tipo": "Incidente", "modulo": "CPU"},
            current_user={"username": "qa_ticket_user"}
        )
        self.assertIsInstance(result, dict)
        self.assertEqual(result["type"], "success")
        self.assertIn("registrado exitosamente", result["message"])

    def test_srv_02_ai_service_resilience_fallback(self):
        """QA-SRV-02: Verify AI assistant graceful degradation when API key is missing."""
        response = ai_service.get_ai_response("¿Cómo optimizar una consulta en SQL Server?", username="qa_user")
        self.assertIsInstance(response, dict)
        self.assertIn("message", response)
        self.assertTrue(len(response["message"]) > 10)

    def test_srv_03_remote_db_service_invalid_connection(self):
        """QA-SRV-03: Verify remote DB executor handles unreachable hosts safely raising RuntimeError."""
        with self.assertRaises(RuntimeError):
            remote_db_service.get_remote_db_connection("Driver={ODBC Driver 18 for SQL Server};Server=192.0.2.1;Database=mockdb;MockToken=test;LoginTimeout=1;")

    # --------------------------------------------------------------------------
    # 5. SECURITY & INJECTION DEFENSE TESTS
    # --------------------------------------------------------------------------
    def test_def_01_dba_cancel_process_sanitization(self):
        """QA-DEF-01: Verify that KILL process endpoint blocks SQL Injection attempts."""
        req = CancelSessionRequest(spid="1; DROP TABLE users;")
        dummy_admin = {"id": 1, "username": "admin", "role": "Administrador"}

        res = action_cancelar(body=req, _=dummy_admin, user=dummy_admin)
        self.assertEqual(res.get("type"), "error")
        self.assertIn("número entero válido", res.get("message"))

    def test_def_02_dba_endpoints_without_selected_instance(self):
        """QA-DEF-02: Verify DBA telemetry endpoints fail gracefully when no instance is selected."""
        dummy_user = {"id": 99, "username": "unselected_user", "role": "Monitor"}
        res_status = action_status(user=dummy_user)
        self.assertEqual(res_status.get("type"), "error")
        self.assertIn("no hay instancia seleccionada", res_status.get("message").lower())

        res_cpu = action_cpu(user=dummy_user)
        self.assertEqual(res_cpu.get("type"), "error")
        self.assertIn("no hay instancia seleccionada", res_cpu.get("message").lower())

        res_discos = action_discos(user=dummy_user)
        self.assertEqual(res_discos.get("type"), "error")
        self.assertIn("no hay instancia seleccionada", res_discos.get("message").lower())

    def test_def_03_historical_cpu_simulation(self):
        """QA-DEF-03: Verify historical CPU telemetry data shape and timestamps."""
        dummy_user = {"id": 1, "username": "admin", "role": "Administrador"}
        res = get_historical_cpu(contract_id=1, _=dummy_user)
        self.assertIsInstance(res, HistoricalCpuResponse)
        self.assertEqual(len(res.labels), 24)
        self.assertEqual(len(res.data), 24)
        self.assertTrue(res.simulated)

    def test_def_04_new_dba_endpoints_without_selected_instance(self):
        """QA-DEF-04: Verify new Erik Darling-inspired endpoints handle missing instance gracefully."""
        dummy_user = {"id": 99, "username": "unselected_user", "role": "Monitor"}

        res_bloqueos = action_bloqueos(user=dummy_user)
        self.assertEqual(res_bloqueos.get("type"), "error")
        self.assertIn("no hay instancia seleccionada", res_bloqueos.get("message").lower())

        res_waits = action_waitstats(user=dummy_user)
        self.assertEqual(res_waits.get("type"), "error")
        self.assertIn("no hay instancia seleccionada", res_waits.get("message").lower())

        res_bloat = action_bloat(user=dummy_user)
        self.assertEqual(res_bloat.get("type"), "error")
        self.assertIn("no hay instancia seleccionada", res_bloat.get("message").lower())

        res_vacuum = action_maintenance(user=dummy_user)
        self.assertEqual(res_vacuum.get("type"), "error")
        self.assertIn("no hay instancia seleccionada", res_vacuum.get("message").lower())

    def test_srv_04_blocking_chain_query_mock_parser(self):
        """QA-SRV-04: Test query_blocking_chain row transformation for SQL Server and Postgres."""
        from unittest.mock import MagicMock
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("OrdersDB", 102, "app_user", "host1", "ERP", 88, "sa", "host2", "SSMS", "RUNNING", 15.4, "X", "dbo.Orders", "SELECT * FROM Orders", "UPDATE Orders SET status=1")
        ]
        sqlserver_res = query_blocking_chain(mock_cursor, "sqlserver")
        self.assertEqual(len(sqlserver_res), 1)
        self.assertEqual(sqlserver_res[0]["Blocked_SPID"], "102")
        self.assertEqual(sqlserver_res[0]["Blocking_SPID"], "88")
        self.assertEqual(sqlserver_res[0]["Lock_Mode"], "X")

        mock_cursor.fetchall.return_value = [
            (2045, "pg_user", "backend_app", "idle in transaction", "Lock: relation", 12.5, 1012, "admin_user", "pgAdmin", "active", "SI (Idle in TX)", 45.2, "SELECT 1", "BEGIN;")
        ]
        pg_res = query_blocking_chain(mock_cursor, "postgres")
        self.assertEqual(len(pg_res), 1)
        self.assertEqual(pg_res[0]["Blocked_PID"], "2045")
        self.assertEqual(pg_res[0]["Blocking_PID"], "1012")
        self.assertEqual(pg_res[0]["Blocker_Idle_In_TX"], "SI (Idle in TX)")

    def test_srv_05_wait_stats_query_mock_parser(self):
        """QA-SRV-05: Test query_wait_stats row transformation for SQL Server and Postgres."""
        from unittest.mock import MagicMock
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("PAGEIOLATCH_SH", 1540, 120.5, 12.0, 10.0, 78.2)
        ]
        sqlserver_res = query_wait_stats(mock_cursor, "sqlserver")
        self.assertEqual(len(sqlserver_res), 1)
        self.assertEqual(sqlserver_res[0]["Tipo_Espera"], "PAGEIOLATCH_SH")
        self.assertEqual(sqlserver_res[0]["CPU_Pressure_Pct"], "10.0%")

        mock_cursor.fetchall.return_value = [
            ("Lock", "relation", 5, 22.4, "alice, bob", "backend_api")
        ]
        pg_res = query_wait_stats(mock_cursor, "postgres")
        self.assertEqual(len(pg_res), 1)
        self.assertEqual(pg_res[0]["Wait_Type"], "Lock")
        self.assertEqual(pg_res[0]["Active_Sessions"], 5)

    def test_srv_06_bloat_fragmentation_mock_parser(self):
        """QA-SRV-06: Test query_bloat_fragmentation for SQL Server and Postgres."""
        from unittest.mock import MagicMock
        mock_cursor = MagicMock()
        # SQL Server
        mock_cursor.fetchall.return_value = [
            ("dbo", "Orders", "PK_Orders", "CLUSTERED", 50000, 120.0, 95.0, 25.0, 20.8, 4500, 1200, "Saludable")
        ]
        sqlserver_res = query_bloat_fragmentation(mock_cursor, "sqlserver")
        self.assertEqual(len(sqlserver_res), 1)
        self.assertEqual(sqlserver_res[0]["Motor"], "SQL Server")
        self.assertEqual(sqlserver_res[0]["Tabla"], "Orders")
        self.assertEqual(sqlserver_res[0]["Desperdicio_Bloat"], "20.8%")

        # PostgreSQL
        mock_cursor.fetchall.return_value = [
            ("public", "invoices", 100000, 25000, 20.0, "50 MB", "40 MB", "10 MB", "2026-10-12 10:00:00", "2026-10-12 10:00:00")
        ]
        pg_res = query_bloat_fragmentation(mock_cursor, "postgres")
        self.assertEqual(len(pg_res), 1)
        self.assertEqual(pg_res[0]["Motor"], "PostgreSQL")
        self.assertEqual(pg_res[0]["Tabla"], "invoices")

    def test_srv_07_maintenance_stats_mock_parser(self):
        """QA-SRV-07: Test query_maintenance_stats for SQL Server and Postgres."""
        from unittest.mock import MagicMock
        mock_cursor = MagicMock()
        # SQL Server
        mock_cursor.fetchall.return_value = [
            ("dbo", "Customers", "IX_Customers_Email", 25000, 7500, 30.0, "2026-09-01 12:00:00", 41, "⚠️ CRÍTICO: Recompilar Stats")
        ]
        sqlserver_res = query_maintenance_stats(mock_cursor, "sqlserver")
        self.assertEqual(len(sqlserver_res), 1)
        self.assertEqual(sqlserver_res[0]["Motor"], "SQL Server")
        self.assertEqual(sqlserver_res[0]["Tabla"], "Customers")
        self.assertIn("CRÍTICO", sqlserver_res[0]["Diagnostico"])

        # PostgreSQL
        mock_cursor.fetchall.side_effect = [
            [(5541, "postgres", "orders", "scanning heap", 1000, 500, 500, 1)],  # active (without dead tuples column)
            [("public", "customers", 800, 10000, 5, 2, "2026-10-11", 8.0)]  # candidates
        ]
        vacuum_res = query_maintenance_stats(mock_cursor, "postgres")
        self.assertEqual(len(vacuum_res), 2)
        self.assertEqual(vacuum_res[0]["Motor"], "PostgreSQL")
        self.assertIn("EN EJECUCIÓN", vacuum_res[0]["Estado"])

    def test_audit_01_log_and_query_repo(self):
        """QA-AUDIT-01: Verify audit logging and retrieval in repository."""
        log_id = audit_repo.log_action(
            db=self.db,
            username="admin",
            action="KILL_TRANSACTION",
            engine="SQL SERVER",
            target_spid=120,
            status="SUCCESS",
            details="Forced termination test"
        )
        self.assertIsNotNone(log_id)
        logs = audit_repo.get_audit_logs(db=self.db, action="KILL_TRANSACTION")
        self.assertTrue(len(logs) >= 1)
        self.assertEqual(logs[0]["username"], "admin")
        self.assertEqual(logs[0]["target_spid"], 120)

    def test_audit_02_admin_endpoint(self):
        """QA-AUDIT-02: Verify admin audit logs endpoint."""
        admin_user = {"id": 1, "username": "admin", "role": "Administrador"}
        logs = list_audit_logs(db=self.db, _=admin_user)
        self.assertIsInstance(logs, list)

    def test_chat_03_clear_history_endpoint(self):
        """QA-CHAT-03: Verify chat clear history endpoint and repository."""
        chat_repo.add_chat_message(self.db, "admin", "Mensaje temporal para limpiar")
        before_count = len(chat_repo.get_chat_history(self.db))
        self.assertGreater(before_count, 0)

        admin_user = {"id": 1, "username": "admin", "role": "Administrador"}
        resp = clear_chat_history_endpoint(db=self.db, _=admin_user)
        self.assertIn("eliminado", resp["message"].lower())
        after_count = len(chat_repo.get_chat_history(self.db))
        self.assertEqual(after_count, 0)

    def test_telemetry_02_overview_endpoint(self):
        """QA-TEL-01: Verify 24h telemetry overview endpoint schema and data series."""
        admin_user = {"id": 1, "username": "admin", "role": "Administrador"}
        res = get_telemetry_overview(user=admin_user)
        self.assertIn("labels", res)
        self.assertIn("cpu_series", res)
        self.assertIn("blocking_series", res)
        self.assertIn("throughput_series", res)
        self.assertIn("wait_types", res)
        self.assertIn("wait_series", res)
        self.assertIn("kpis", res)
        self.assertEqual(len(res["labels"]), 24)
        self.assertEqual(len(res["cpu_series"]), 24)
        self.assertIn("engine", res["kpis"])

    def test_srv_08_local_dba_intel(self):
        """QA-SRV-08: Verify offline intelligent DBA responses for keywords."""
        resp_wait = ai_service.get_ai_response("¿Por qué tengo espera PAGEIOLATCH en la base de datos?", username="dba_lead")
        self.assertIn("PAGEIOLATCH", resp_wait["message"])
        self.assertIn("Buffer Pool", resp_wait["message"])

        resp_help = ai_service.get_ai_response("ayuda", username="dba_lead")
        self.assertIn("Guía Rápida", resp_help["message"])


if __name__ == "__main__":
    unittest.main()

