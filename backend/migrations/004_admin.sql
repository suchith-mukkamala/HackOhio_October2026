-- Admin flag, set when someone redeems the secret ADMIN_CODE (additive, safe to re-run)
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;
