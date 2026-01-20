# scripts/verify_db_tables.py
import sys
import os
from sqlalchemy import text
from dotenv import load_dotenv

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, '..')
load_dotenv(os.path.join(project_root, ".env.local"))
sys.path.append(os.path.abspath(project_root))

from database.db import engine

def verify_tables():
    print("🔍 Verifying Database Tables...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [row[0] for row in result]
        
    required = ["global_concept_stats", "global_edge_stats"]
    missing = [t for t in required if t not in tables]
    
    if missing:
        print(f"❌ Missing Phase 4 Tables: {missing}")
        sys.exit(1)
    else:
        print("✅ Phase 4 Tables Exist.")
        
        # Check columns for one
        with engine.connect() as conn:
            cols = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'global_edge_stats'"))
            columns = [row[0] for row in cols]
            print(f"   Columns in GlobalEdgeStats: {columns}")
            if "contested_count" in columns and "weighted_frequency" in columns:
                 print("✅ Schema Columns Verified.")
            else:
                 print("❌ Columns Missing!")
                 sys.exit(1)

if __name__ == "__main__":
    verify_tables()
