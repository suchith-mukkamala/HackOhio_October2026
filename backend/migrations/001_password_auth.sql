-- For existing PostgreSQL databases: apply once before starting the updated backend.
-- Adds nullable credentials for compatibility with existing GitHub/demo accounts.
-- Unique indexes deliberately fail on duplicate identities rather than deleting data.
BEGIN;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS username VARCHAR(50);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS password_hash VARCHAR;
ALTER TABLE "user" ALTER COLUMN username DROP NOT NULL;
ALTER TABLE "user" ALTER COLUMN password_hash DROP NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ix_user_username ON "user" (username);
CREATE UNIQUE INDEX IF NOT EXISTS ix_user_email ON "user" (email);
COMMIT;
