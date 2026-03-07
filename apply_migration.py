"""Run a specific migration file by name."""
import sys
import os
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv(".env.local")

from database.db import engine

def apply_migration(migration_filename: str):
    migration_path = os.path.join(os.path.dirname(__file__), "migrations", migration_filename)
    with open(migration_path, 'r') as file:
        sql_commands = file.read()
        
    with engine.begin() as conn:
        conn.execute(text(sql_commands))
            
    print(f"Migration '{migration_filename}' applied successfully.")

if __name__ == "__main__":
    filename = sys.argv[1] if len(sys.argv) > 1 else "add_updated_at.sql"
    apply_migration(filename)
