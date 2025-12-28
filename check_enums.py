
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load env
load_dotenv(".env.local")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Try constructing from components if URL not set directly
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    server = os.getenv("POSTGRES_SERVER", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "vra_db")
    DATABASE_URL = f"postgresql://{user}:{password}@{server}:{port}/{db}"

print(f"Connecting to: {DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print("\n--- ENUM: userrole ---")
        try:
            result = conn.execute(text("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = 'userrole'"))
            for row in result:
                print(f" - {row[0]}")
        except Exception as e:
            print(f"Error checking userrole: {e}")

        print("\n--- ENUM: sessionstatus ---")
        try:
            result = conn.execute(text("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = 'sessionstatus'"))
            for row in result:
                print(f" - {row[0]}")
        except Exception as e:
            print(f"Error checking sessionstatus: {e}")

except Exception as e:
    print(f"Connection failed: {e}")
