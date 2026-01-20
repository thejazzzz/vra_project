# scripts/migrate_graph_analytics.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sqlalchemy import text
from dotenv import load_dotenv

# Load env before importing db
load_dotenv(".env.local")

from database.db import engine

def migrate():
    print("Running migration: ADD research_analytics to graphs table...")
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE graphs ADD COLUMN IF NOT EXISTS research_analytics JSON;"))
            conn.commit()
            print("✅ Migration successful.")
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            sys.exit(1)
if __name__ == "__main__":
    migrate()
