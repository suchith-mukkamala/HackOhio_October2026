"""Isolated auth regression checks: python -m unittest discover -s tests -v."""
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# Never connect to the configured RDS instance from this test suite.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "isolated-test-signing-key-at-least-32-bytes"

import jwt
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.auth import COOKIE
from app.config import settings
from app.db import get_session
from app.models import User
from app.routers import auth, users


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        app = FastAPI()
        app.include_router(auth.router, prefix="/api")
        app.include_router(users.router, prefix="/api")
        app.dependency_overrides[get_session] = lambda: self.session
        self.client = TestClient(app)
        self.payload = dict(username="builder", name="Test Builder", email="builder@example.com", password="a-long-test-password")

    def tearDown(self):
        self.client.close()
        self.session.close()
        self.engine.dispose()

    def register(self, **changes):
        return self.client.post("/api/auth/register", json={**self.payload, **changes})

    def test_register_hashes_password_and_signs_in(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.text)
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertIn("SameSite=lax", response.headers["set-cookie"])
        user = self.session.exec(select(User)).one()
        self.assertNotEqual(user.password_hash, self.payload["password"])
        self.assertTrue(auth.password_hasher.verify(self.payload["password"], user.password_hash))
        self.assertEqual(self.client.get("/api/me").json()["id"], user.id)

    def test_duplicate_username_and_email(self):
        self.register()
        self.assertEqual(self.register(email="other@example.com").status_code, 409)
        self.assertEqual(self.register(username="other", email="BUILDER@example.com").status_code, 409)

    def test_integrity_race_returns_conflict_and_rolls_back(self):
        with patch.object(self.session, "commit", side_effect=IntegrityError("insert", {}, Exception("duplicate"))), patch.object(self.session, "rollback", wraps=self.session.rollback) as rollback:
            self.assertEqual(self.register().status_code, 409)
            rollback.assert_called_once()

    def test_email_uniqueness_is_enforced_by_database(self):
        self.session.add_all([User(name="First", email="same@example.com"), User(name="Second", email="same@example.com")])
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_invalid_registration(self):
        for changes in [dict(password="short"), dict(email="bad"), dict(username="  "), dict(name="   ")]:
            with self.subTest(changes=changes):
                self.assertEqual(self.register(**changes).status_code, 422)

    def test_identity_whitespace_is_trimmed(self):
        self.assertEqual(self.register(username=" builder ", name=" Test Builder ").json()["name"], "Test Builder")
        self.assertEqual(self.client.post("/api/auth/login", json={"username": " builder ", "password": self.payload["password"]}).status_code, 200)

    def test_login_logout_and_wrong_password(self):
        self.register()
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 204)
        self.assertEqual(self.client.get("/api/me").status_code, 401)
        for username, password in [("builder", "wrong"), ("missing", "wrong")]:
            response = self.client.post("/api/auth/login", json=dict(username=username, password=password))
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["detail"], "Invalid username or password")
        self.assertEqual(self.client.post("/api/auth/login", json={"username": "builder", "password": self.payload["password"]}).status_code, 200)
        self.assertEqual(self.client.get("/api/me").status_code, 200)

    def test_passwordless_and_corrupt_hash_accounts(self):
        for name, hashed in [("passwordless", None), ("corrupt", "not-a-valid-hash")]:
            self.session.add(User(name=name, username=name, password_hash=hashed))
        self.session.commit()
        for name in ["passwordless", "corrupt"]:
            self.assertEqual(self.client.post("/api/auth/login", json={"username": name, "password": "some-password"}).status_code, 401)

    def test_demo_personas_and_disabled_mode(self):
        user = User(name="Demo Builder")
        self.session.add(user)
        self.session.commit()
        with patch.object(settings, "demo_mode", True):
            self.assertEqual(len(self.client.get("/api/auth/demo/personas").json()), 1)
            self.assertEqual(self.client.post(f"/api/auth/demo/{user.id}").status_code, 204)
            self.assertEqual(self.client.get("/api/me").status_code, 200)
            self.assertEqual(self.client.post("/api/auth/demo/99999").status_code, 404)
        with patch.object(settings, "demo_mode", False):
            self.assertEqual(self.client.get("/api/auth/demo/personas").json(), [])
            self.assertEqual(self.client.post(f"/api/auth/demo/{user.id}").status_code, 403)

    def test_invalid_and_expired_sessions(self):
        payloads = [{"sub": "not-an-id"}, {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)}, {"sub": "9999"}]
        for payload in payloads:
            self.client.cookies.set(COOKIE, jwt.encode(payload, settings.jwt_secret, algorithm="HS256"))
            self.assertEqual(self.client.get("/api/me").status_code, 401)

    def test_github_state_and_secure_cookies(self):
        with patch.object(settings, "github_client_id", "test-client"), patch.object(settings, "secure_cookies", True):
            response = self.client.get("/api/auth/github/login", follow_redirects=False)
            self.assertEqual(response.status_code, 307)
            self.assertIn("state=", response.headers["location"])
            self.assertIn("Secure", response.headers["set-cookie"])
            response = self.register()
            self.assertIn("Secure", response.headers["set-cookie"])
        with patch.object(auth.github, "exchange_code") as exchange:
            self.assertEqual(self.client.get("/api/auth/github/callback?code=test&state=wrong", follow_redirects=False).status_code, 400)
            exchange.assert_not_called()

    def test_github_first_login_and_returning_login(self):
        self.client.cookies.set("oauth_state", "test-state")
        with patch.object(auth.github, "exchange_code", return_value="private-github-token"), patch.object(auth.github, "get_viewer", return_value={"login": "octocat", "name": "Octo Cat", "avatar_url": "https://example.com/avatar.png", "bio": "Builder"}):
            response = self.client.get("/api/auth/github/callback?code=test&state=test-state", follow_redirects=False)
            self.assertEqual(response.status_code, 307)
            self.assertTrue(response.headers["location"].endswith("/feed"))
            self.assertNotIn("private-github-token", self.client.get("/api/me").text)
            self.client.cookies.set("oauth_state", "test-state")
            self.assertEqual(self.client.get("/api/auth/github/callback?code=test&state=test-state", follow_redirects=False).status_code, 307)
        self.assertEqual(len(self.session.exec(select(User)).all()), 1)

    def test_documented_app_import(self):
        from app.main import app
        self.assertIn("/api/auth/login", app.openapi()["paths"])

    def test_github_upstream_failure(self):
        self.client.cookies.set("oauth_state", "test-state")
        with patch.object(auth.github, "exchange_code", side_effect=httpx.ConnectError("upstream unavailable")):
            response = self.client.get("/api/auth/github/callback?code=test&state=test-state", follow_redirects=False)
            self.assertEqual(response.status_code, 502)
            self.assertNotIn("upstream unavailable", response.text)


if __name__ == "__main__":
    unittest.main()
