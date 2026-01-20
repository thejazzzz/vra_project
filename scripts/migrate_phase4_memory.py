# scripts/migrate_phase4_memory.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv(".env.local")

from database.db import engine, Base
from database.models.memory_model import GlobalConceptStats, GlobalEdgeStats

def migrate():
    print("Running Phase 4 Migration: Create Global Memory Tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Phase 4 Tables Created (GlobalConceptStats, GlobalEdgeStats).")
    except Exception as e:
        print(f"❌ Migration Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
