# scripts/migrate_overrides.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv(".env.local")

from database.db import engine, Base
from database.models.graph_model import UserGraphOverride

def migrate():
    print("Running migration: Create user_graph_overrides table...")
    # SQLAlchemy create_all blindly creates missing tables
    Base.metadata.create_all(bind=engine)
    print("✅ Migration successful (if table was missing).")

if __name__ == "__main__":
    migrate()
