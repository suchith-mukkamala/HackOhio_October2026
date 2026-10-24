import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

# Load backend/.env no matter where uvicorn was started
BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _database_url() -> str:
    """The AWS RDS Postgres database, from the DB_* fields in backend/.env."""
    if os.getenv("DATABASE_URL"):  # explicit override, used by the test suite
        return os.environ["DATABASE_URL"]
    missing = [k for k in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD") if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Set {', '.join(missing)} in backend/.env (see .env.example)")
    return URL.create(
        "postgresql+psycopg",
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.environ["DB_NAME"],
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    ).render_as_string(hide_password=False)


class Settings:
    database_url = _database_url()
    jwt_secret = os.getenv("JWT_SECRET", "dev-secret-change-me")
    github_client_id = os.getenv("GITHUB_CLIENT_ID", "")
    github_client_secret = os.getenv("GITHUB_CLIENT_SECRET", "")
    github_redirect_uri = os.getenv(
        "GITHUB_REDIRECT_URI", "http://localhost:8000/api/auth/github/callback"
    )
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/api/auth/google/callback")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")  # resume reading
    claude_model = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
    demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
    # Secret code that makes whoever types it an admin. Empty means admin access is turned off.
    admin_code = os.getenv("ADMIN_CODE", "").strip()
    # Usernames that are always admins, comma separated: neel,rohan,suchith,adi. Empty means none.
    admin_usernames = [u.strip().lower() for u in os.getenv("ADMIN_USERNAMES", "").split(",") if u.strip()]
    # Cookies must be Secure behind HTTPS (App Runner / Vercel) but not on localhost
    secure_cookies = os.getenv("SECURE_COOKIES", "false").lower() == "true"


settings = Settings()
