import sys
import os

# Add the project root to the python path so we can import from database
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables from .env.local (or .env)
env_path = os.path.join(os.path.dirname(__file__), '..', '.env.local')
if not os.path.exists(env_path):
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

from database.db import engine

def reset_database():
    """
    Truncates all tables in the database to clear all data while preserving structure.
    """
    print("WARNING: This will delete ALL data from the following tables:")
    tables = [
        "users",
        "research_sessions",
        "audit_logs",
        "refresh_tokens",
        "graphs",
        "papers",
        "workflow_states"
    ]
    for t in tables:
        print(f" - {t}")
    
    print("\nThe schema (structure) will be preserved.")
    
    confirm = input("Are you sure you want to proceed? (yes/no): ")
    if confirm.lower() != "yes":
        print("Operation cancelled.")
        return

    try:
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        
        # Verify all requested tables exist
        missing_tables = [t for t in tables if t not in existing_tables]
        if missing_tables:
            print(f"Error: The following tables were not found in the database: {missing_tables}")
            return

        with engine.begin() as connection:
            # Quote identifiers for safety
            preparer = engine.dialect.identifier_preparer
            quoted_tables = [preparer.quote(t) for t in tables]
            table_list_str = ", ".join(quoted_tables)
            
            print(f"Truncating tables: {table_list_str}...")
            
            connection.execute(text(f"TRUNCATE TABLE {table_list_str} RESTART IDENTITY CASCADE;"))
            
            print("Successfully reset all tables.")
    except Exception as e:
        print(f"Error resetting database: {e}")

if __name__ == "__main__":
    reset_database()
