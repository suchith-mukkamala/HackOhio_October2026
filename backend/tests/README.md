Run the authentication regression suite from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests use an isolated in-memory SQLite database and mocked GitHub responses.
They do not connect to RDS or perform a real GitHub OAuth exchange.

To prepare the PostgreSQL database configured in `backend/.env`, run from `backend/`:

```powershell
.\.venv\Scripts\python.exe migrate_database.py
.\.venv\Scripts\python.exe check_database.py
.\.venv\Scripts\python.exe tests/verify_database_auth.py
```

The migration creates missing app tables and applies
`backend/migrations/001_password_auth.sql` transactionally without resetting data.
The last command verifies auth against the configured database using a temporary
account inside a transaction, then rolls it back. It is an explicit integration
check and is not included in unittest discovery.

`create_all()` only creates missing
tables; it does not add columns to existing tables. The migration preserves
existing users and leaves GitHub/demo accounts without local passwords. Duplicate
usernames or emails must be resolved before its unique indexes can be created.
Never drop tables on the shared AWS database.

Existing SQLite databases also need nullable `username` and `password_hash`
columns and unique indexes on `username` and `email`. The PostgreSQL migration
is not SQLite-compatible. A new SQLite database is created with the updated schema.

Set a random, persistent `JWT_SECRET` in `backend/.env` before deployment; the
development fallback in config is not appropriate for deployed sessions.
