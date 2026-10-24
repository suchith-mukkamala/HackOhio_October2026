from collections.abc import Iterator

from sqlalchemy import bindparam, text
from sqlmodel import Session, SQLModel, create_engine

from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)

_ready = False


def init_db() -> None:
    """Bring the database schema up to date. Runs once per process, so it is safe to call anywhere."""
    global _ready
    if _ready:
        return
    from . import models  # noqa: F401  (registers tables)

    SQLModel.metadata.create_all(engine)  # creates missing tables only
    _add_missing_columns()
    _promote_admins()
    _ready = True


def _add_missing_columns() -> None:
    """create_all never alters a table that already exists, so new columns on old tables go here.

    Every statement must be additive and safe to re-run (IF NOT EXISTS). Postgres only:
    a brand-new SQLite database gets its columns straight from the models.
    """
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as connection:
        connection.exec_driver_sql('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE')


def _promote_admins() -> None:
    """Accounts named in the ADMIN_USERNAMES setting become admins. Existing accounts only."""
    if not settings.admin_usernames:
        return
    statement = text('UPDATE "user" SET is_admin = TRUE WHERE LOWER(username) IN :names AND is_admin = FALSE')
    with engine.begin() as connection:
        connection.execute(statement.bindparams(bindparam("names", expanding=True)), {"names": settings.admin_usernames})


def get_session() -> Iterator[Session]:
    init_db()  # does nothing after the first call, but covers serverless starts that skip the lifespan hook
    with Session(engine) as session:
        yield session
