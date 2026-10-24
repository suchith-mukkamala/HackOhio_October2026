"""Check the configured database without logging credentials."""
import sys

from sqlalchemy import inspect, text

from app.db import engine


def main():
    print(f"Database: {engine.dialect.name}; host: {engine.url.host or 'local'}; name: {engine.url.database}")
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            print("Connection: OK")
            inspector = inspect(connection)
            if inspector.has_table("user"):
                columns = {column["name"] for column in inspector.get_columns("user")}
                print("Auth columns present:", {name: name in columns for name in ("username", "password_hash", "email")})
            else:
                print("User table does not exist yet.")
            if engine.dialect.name == "postgresql":
                print("TLS:", connection.execute(text("SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()")).scalar())
    except Exception as exc:
        # Avoid SQLAlchemy exceptions, which can include connection secrets or query values.
        original = getattr(exc, "orig", exc)
        print(f"Connection check failed: {type(original).__name__}")
        print("SQLSTATE:", getattr(original, "sqlstate", None) or "unavailable")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
