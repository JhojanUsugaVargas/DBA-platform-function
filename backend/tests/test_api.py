"""Backend Unit Tests for Core, Auth, Security and Repositories."""
import os
import unittest

os.environ["SECRET_KEY"] = "test-secret-key-12345"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DB_SCHEMA"] = ""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=test_engine))

import app.db.session as app_session
app_session.engine = test_engine
app_session.SessionLocal = TestingSessionLocal

from app.db.base import Base
from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    encrypt_data,
    decrypt_data,
)
from app.models import User, Contract, Instance
from app.repositories import user_repo, contract_repo, chat_repo


class TestDataCheckCore(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=test_engine)

    def setUp(self):
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()

    def test_security_hashing(self):
        pwd = "SecretPassword123!"
        hashed = get_password_hash(pwd)
        self.assertTrue(verify_password(pwd, hashed))
        self.assertFalse(verify_password("WrongPassword", hashed))

    def test_jwt_tokens(self):
        token = create_access_token({"sub": "testuser"})
        payload = decode_access_token(token)
        self.assertEqual(payload.get("sub"), "testuser")
        self.assertIn("exp", payload)

    def test_fernet_encryption(self):
        plain = "MockEngine=InMemory;MockDatabase=testdb;MockKey=mock_secret_token_123;"
        encrypted = encrypt_data(plain)
        self.assertNotEqual(plain, encrypted)
        decrypted = decrypt_data(encrypted)
        self.assertEqual(plain, decrypted)

    def test_user_repository(self):
        user = user_repo.create_user(
            db=self.db,
            username="test_dev_user",
            full_name="Test Dev",
            hashed_password=get_password_hash("DevPass123!"),
            role="Monitor"
        )
        self.assertIsNotNone(user.id)
        found = user_repo.get_by_username(self.db, "test_dev_user")
        self.assertEqual(found.id, user.id)

    def test_contract_and_instance_repository(self):
        contract_data = contract_repo.add_contract(self.db, "Test Contract")
        contract_id = contract_data["id"]
        self.assertIsNotNone(contract_id)

        inst = contract_repo.add_instance(
            db=self.db,
            contract_id=contract_id,
            name="SQL_TEST_01",
            conn_str="MockEngine=InMemory;MockDatabase=testdb;MockKey=mock_secret_token_123;"
        )
        self.assertIsNotNone(inst.id)

        instances = contract_repo.get_instances_by_contract(self.db, contract_id)
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]["name"], "SQL_TEST_01")
        self.assertEqual(instances[0]["conn_str"], "MockEngine=InMemory;MockDatabase=testdb;MockKey=mock_secret_token_123;")

    def test_chat_repository(self):
        msg_id = chat_repo.add_chat_message(self.db, "admin", "Hola asistente")
        self.assertIsNotNone(msg_id)
        history = chat_repo.get_chat_history(self.db)
        self.assertTrue(any(m["content"] == "Hola asistente" for m in history))


if __name__ == "__main__":
    unittest.main()
