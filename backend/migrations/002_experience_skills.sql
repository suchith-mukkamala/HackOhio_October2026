-- Skills read from each resume entry (additive, safe to re-run)
ALTER TABLE experience ADD COLUMN IF NOT EXISTS skills JSON;
