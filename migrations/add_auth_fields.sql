-- Add password hash and email verified fields to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret VARCHAR(255) NULL;

-- Create VerificationTokenType enum
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'verificationtokentype') THEN
        CREATE TYPE verificationtokentype AS ENUM ('EMAIL_VERIFY', 'PASSWORD_RESET', 'MAGIC_LINK');
    END IF;
END
$$;

-- Create verification_tokens table
CREATE TABLE IF NOT EXISTS verification_tokens (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR NOT NULL UNIQUE,
    type verificationtokentype NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_verification_tokens_user_id ON verification_tokens(user_id);