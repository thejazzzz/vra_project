ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Create trigger function to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop trigger if exists to ensure idempotency
DROP TRIGGER IF EXISTS update_updated_at_trigger ON users;

-- Create trigger to call function before update
CREATE TRIGGER update_updated_at_trigger
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
