"""Create missing app tables and apply the additive PostgreSQL migrations in migrations/."""
from pathlib import Path

from sqlalchemy import inspect
from sqlmodel import SQLModel

from app import models  # noqa: F401: register every table before creating metadata
from app.db import engine


def migrate():
    if engine.dialect.name != "postgresql":
        raise RuntimeError("This migration runner is for PostgreSQL databases only.")
    # Every migration is additive and idempotent, so run them all in order.
    sql = "\n".join(f.read_text() for f in sorted((Path(__file__).parent / "migrations").glob("*.sql")))
    # Let SQLAlchemy own the transaction, including creation of missing tables.
    sql = sql.replace("BEGIN;", "").replace("COMMIT;", "")
    with engine.begin() as connection:
        SQLModel.metadata.create_all(connection)
        for statement in sql.split(";"):
            if statement.strip():
                connection.exec_driver_sql(statement)
        inspector = inspect(connection)
        unique_columns = {
            tuple(index["column_names"])
            for index in inspector.get_indexes("user") if index.get("unique")
        } | {
            tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints("user")
        }
        if not {("username",), ("email",)} <= unique_columns:
            raise RuntimeError("Auth identity indexes must be unique; migration rolled back.")
    print("PostgreSQL schema ready. Existing records preserved.")


if __name__ == "__main__":
    migrate()
