-- Migration: Add used_at column to verification_tokens table
ALTER TABLE verification_tokens
ADD COLUMN IF NOT EXISTS used_at TIMESTAMP NULL;
