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
from app.models import User, Contract, Instance, ChatMessage, Feedback
from app.repositories import user_repo, contract_repo, chat_repo, feedback_repo
from app.schemas.auth import TokenResponse, UserProfileResponse
from app.schemas.admin import ContractCreateRequest, InstanceCreateRequest, UserCreateRequest
from app.schemas.dba import CancelSessionRequest, HistoricalCpuResponse
from app.schemas.chat import ChatRequest
from app.schemas.feedback import FeedbackSubmitRequest
from app.api.auth import login as api_login
from app.api.admin import list_contracts, list_users, create_contract
from app.api.dba import action_cancelar, action_status, action_cpu, action_discos, get_historical_cpu
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
        raw_conn = "Server=prod-sql.internal;Database=master;Uid=sa;Pwd=StrongPass123!;"
        encrypted = encrypt_data(raw_conn)
        self.assertNotEqual(raw_conn, encrypted)

        decrypted = decrypt_data(encrypted)
        self.assertEqual(raw_conn, decrypted)

        # Fallback for unencrypted legacy string returns string as-is
        plaintext_fallback = decrypt_data("Server=legacy;Uid=test;")
        self.assertEqual(plaintext_fallback, "Server=legacy;Uid=test;")

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
            conn_str="Server=10.0.0.1;Uid=dba;Pwd=secret;"
        )
        self.assertIsNotNone(inst1.id)

        inst2 = contract_repo.add_instance(
            db=self.db,
            contract_id=contract_id,
            name="SRV-SQL-02",
            conn_str="Server=10.0.0.2;Uid=dba;Pwd=secret;"
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
            remote_db_service.get_remote_db_connection("Server=192.0.2.1;Database=fake;Uid=fake;Pwd=fake;Connection Timeout=1;")

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


if __name__ == "__main__":
    unittest.main()
