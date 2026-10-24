r"""Explicit integration check against the configured DB; all test data is rolled back.

Run manually: .venv\Scripts\python.exe tests/verify_database_auth.py
Not included in unittest discovery.
"""
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, select

from app.config import settings
from app.db import engine, get_session
from app.models import User
from app.routers import auth, users


def verify():
    identity = "authcheck_" + secrets.token_hex(8)
    password = secrets.token_urlsafe(24)
    # Sessions can commit their savepoints while the outer transaction retains ownership.
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                app = FastAPI()
                app.include_router(auth.router, prefix="/api")
                app.include_router(users.router, prefix="/api")
                app.dependency_overrides[get_session] = lambda: session
                with TestClient(app, base_url="https://testserver" if settings.secure_cookies else "http://testserver") as client:
                    payload = dict(username=identity, name="Database Auth Check", email=f"{identity}@example.com", password=password)
                    assert client.post("/api/auth/register", json=payload).status_code == 201, "registration failed"
                    user = session.exec(select(User).where(User.username == identity)).one()
                    assert user.password_hash != password and auth.password_hasher.verify(password, user.password_hash), "password not hashed"
                    assert client.get("/api/me").json()["id"] == user.id, "registration cookie failed"
                    assert client.post("/api/auth/register", json=payload).status_code == 409, "duplicate not rejected"
                    assert client.post("/api/auth/logout").status_code == 204
                    assert client.get("/api/me").status_code == 401, "logout failed"
                    assert client.post("/api/auth/login", json=dict(username=identity, password="wrong-password")).status_code == 401
                    assert client.post("/api/auth/login", json=dict(username=identity, password=password)).status_code == 200, "login failed"
                    assert client.get("/api/me").json()["id"] == user.id, "login cookie failed"
                    print("Registration, hashing, duplicate detection, login, logout, and authenticated /me: OK")
        finally:
            transaction.rollback()
        assert connection.execute(text('SELECT count(*) FROM "user" WHERE username = :identity'), {"identity": identity}).scalar() == 0, "test account cleanup failed"
        print("Test account rolled back; no test user retained.")


if __name__ == "__main__":
    verify()
