"""Tests de privacidad: consentimiento, exportaci\u00f3n, supresi\u00f3n y baja de correos."""
import os
import unittest

os.environ["SECRET_KEY"] = "test-secret-key-12345"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DB_SCHEMA"] = ""

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=test_engine))

import app.db.session as app_session
app_session.engine = test_engine
app_session.SessionLocal = TestingSessionLocal

from app.db.base import Base
from app.models import User, Feedback, ChatMessage, AuditLog
from app.core.config import settings
from app.core.security import (
    get_password_hash,
    create_access_token,
    create_unsubscribe_token,
    decode_unsubscribe_token,
    decode_access_token,
)
from app.repositories import user_repo, audit_repo
from app.services import privacy_service
from app.schemas.auth import DeleteAccountRequest
from app.schemas.feedback import FeedbackSubmitRequest
from app.api.auth import delete_my_account, export_my_data, accept_legal_documents, unsubscribe
from app.api.feedback import submit_feedback


class TestPrivacy(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=test_engine)

    def setUp(self):
        self.db = TestingSessionLocal()
        self.user = user_repo.create_user(
            db=self.db, username="priv_user", full_name="Priv User",
            hashed_password=get_password_hash("Secret123!"), role="Monitor",
            email="priv_user@example.com",
        )
            email="priv_user@example.com",
        )
        self.db.add(Feedback(user_id=self.user.id, rating=5, comment="hola"))
        self.db.add(ChatMessage(user_id=self.user.id, content="mensaje"))
        self.db.commit()
        audit_repo.log_action(self.db, "priv_user", "TEST_ACTION", details="priv_user hizo algo")

    def tearDown(self):
        self.db.query(AuditLog).delete()
        self.db.query(Feedback).delete()
        self.db.query(ChatMessage).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def test_consent_required_until_accepted(self):
        self.assertTrue(privacy_service.consent_required(self.user))
        accept_legal_documents(db=self.db, current_user={"username": "priv_user"})
        self.db.refresh(self.user)
        self.assertFalse(privacy_service.consent_required(self.user))
        self.assertEqual(self.user.consent_version, settings.LEGAL_VERSION)
        self.assertIsNotNone(self.user.consent_accepted_at)

    def test_export_contains_data_but_not_password_hash(self):
        data = export_my_data(db=self.db, current_user={"username": "priv_user"})
        self.assertEqual(data["profile"]["email"], "priv_user@example.com")
        self.assertEqual(len(data["feedback_and_tickets"]), 1)
        self.assertEqual(len(data["chat_messages"]), 1)
        self.assertNotIn("hashed_password", str(data))

    def test_delete_account_requires_correct_password(self):
        with self.assertRaises(HTTPException) as ctx:
            delete_my_account(DeleteAccountRequest(password="mala"), db=self.db,
                              current_user={"username": "priv_user"})
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIsNotNone(user_repo.get_by_username(self.db, "priv_user"))

    def test_delete_account_erases_data_and_anonymizes_audit(self):
        # Hay otro admin, as\u00ed que no aplica el bloqueo de \u00fanico administrador
        res = delete_my_account(DeleteAccountRequest(password="Secret123!"), db=self.db,
                                current_user={"username": "priv_user"})
        self.assertTrue(res["success"])
        self.assertIsNone(user_repo.get_by_username(self.db, "priv_user"))
        self.assertEqual(self.db.query(Feedback).count(), 0)
        self.assertEqual(self.db.query(ChatMessage).count(), 0)
        logs = self.db.query(AuditLog).all()
        self.assertTrue(logs)
        for log in logs:
            self.assertNotEqual(log.username, "priv_user")
            self.assertNotIn("priv_user", log.details or "")

    def test_last_admin_cannot_delete_account(self):
        self.db.query(User).filter(User.id != self.user.id).delete()
        self.user.role = "Administrador"
        self.db.commit()
        with self.assertRaises(HTTPException) as ctx:
            delete_my_account(DeleteAccountRequest(password="Secret123!"), db=self.db,
                              current_user={"username": "priv_user"})
        self.assertEqual(ctx.exception.status_code, 400)

    def test_unsubscribe_token_flow_and_isolation(self):
        token = create_unsubscribe_token("priv_user")
        self.assertEqual(decode_unsubscribe_token(token), "priv_user")
        # Un token de baja nunca debe servir como token de sesi\u00f3n
        self.assertEqual(decode_access_token(token), {})
        # Un token de sesi\u00f3n nunca debe servir para darse de baja
        self.assertIsNone(decode_unsubscribe_token(create_access_token({"sub": "priv_user"})))

        resp = unsubscribe(token=token, db=self.db)
        self.assertEqual(resp.status_code, 200)
        self.db.refresh(self.user)
        self.assertTrue(self.user.email_opt_out)

        bad = unsubscribe(token="token-invalido", db=self.db)
        self.assertIn(b"no v", bad.body.lower())

    def test_feedback_requires_explicit_consent(self):
        with self.assertRaises(HTTPException) as ctx:
            submit_feedback(FeedbackSubmitRequest(rating=5, comment="x"), db=self.db,
                            user={"username": "priv_user"})
        self.assertEqual(ctx.exception.status_code, 400)
        ok = submit_feedback(FeedbackSubmitRequest(rating=5, comment="x", consent_confirmed=True),
                             db=self.db, user={"username": "priv_user"})
        self.assertTrue(ok["success"])


if __name__ == "__main__":
    unittest.main()
