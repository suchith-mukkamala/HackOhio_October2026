import os
from pathlib import Path

from dotenv import load_dotenv

# Resolve .env and relative SQLite paths from backend/, not from wherever uvicorn was started
BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./keystone.db")
    if url.startswith("sqlite:///./"):
        url = f"sqlite:///{(BACKEND_DIR / url.removeprefix('sqlite:///./')).as_posix()}"
    return url


class Settings:
    database_url = _database_url()
    jwt_secret = os.getenv("JWT_SECRET", "dev-secret-change-me")
    github_client_id = os.getenv("GITHUB_CLIENT_ID", "")
    github_client_secret = os.getenv("GITHUB_CLIENT_SECRET", "")
    github_redirect_uri = os.getenv(
        "GITHUB_REDIRECT_URI", "http://localhost:8000/api/auth/github/callback"
    )
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    claude_model = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    # Cookies must be Secure behind HTTPS (App Runner / Vercel) but not on localhost
    secure_cookies = os.getenv("SECURE_COOKIES", "false").lower() == "true"


settings = Settings()
