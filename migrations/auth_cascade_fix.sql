-- Migration: Fix Auth Cascades and Constraints
-- Run these commands in your SQL client (e.g., pgAdmin, psql) to update the existing schema.

BEGIN;

-- 1. Update Foreign Key to support CASCADE DELETE
-- First, drop the old constraint (Constraint name might vary, check "\d refresh_tokens" in psql if this fails)
ALTER TABLE refresh_tokens DROP CONSTRAINT IF EXISTS refresh_tokens_user_id_fkey;

-- Add new constraint with ON DELETE CASCADE
ALTER TABLE refresh_tokens 
    ADD CONSTRAINT refresh_tokens_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- 2. Enforce Uniqueness on token_hash
-- Drop the old standard index if it exists (SQLAlchemy creates ix_tablename_columnname by default)
DROP INDEX IF EXISTS ix_refresh_tokens_token_hash;

-- WARNING: The following deduplication operation may be slow on very large tables.
-- RECOMMENDATION: Test on staging first. For huge datasets, valid strategy is to adding an index on (token_hash, created_at) first or running in batches.

DO $$
BEGIN
    -- Verify created_at column exists to ensure correct ordering logic
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'refresh_tokens' AND column_name = 'created_at'
    ) THEN
        RAISE EXCEPTION 'Column created_at does not exist in refresh_tokens table. Cannot safely determine most recent token for deduplication.';
    END IF;

    -- Remove duplicate token_hash values (keep the most recent token for each hash)
    DELETE FROM refresh_tokens
    WHERE id IN (
        SELECT id
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY token_hash ORDER BY created_at DESC, id DESC) as rn
            FROM refresh_tokens
        ) t
        WHERE t.rn > 1
    );
END $$ LANGUAGE plpgsql;

-- Add UNIQUE constraint (this automatically creates a unique index)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'refresh_tokens_token_hash_key'
    ) THEN
        ALTER TABLE refresh_tokens ADD CONSTRAINT refresh_tokens_token_hash_key UNIQUE (token_hash);
    END IF;
END $$ LANGUAGE plpgsql;
COMMIT;
