# scripts/standardize_graph_queries.py
import os
from sqlalchemy import text
from database.db import engine, SessionLocal
from database.models.graph_model import Graph
from database.models.auth_models import ResearchSession
from database.models.workflow_state_model import WorkflowState

def migrate():
    print("🚀 Starting Data Migration: Standardizing Query Strings...")
    
    with SessionLocal() as db:
        try:
            # 1. Update Graphs table
            print("Updating 'graphs' table...")
            graphs = db.query(Graph).all()
            for g in graphs:
                g.query = g.query.strip().lower()
            
            # 2. Update ResearchSessions table
            print("Updating 'research_sessions' table...")
            sessions = db.query(ResearchSession).all()
            for s in sessions:
                s.query = s.query.strip().lower()

            # 3. Update WorkflowStates table
            print("Updating 'workflow_states' table...")
            states = db.query(WorkflowState).all()
            for ws in states:
                ws.query = ws.query.strip().lower()

            db.commit()
            print("✅ Database migration successful!")
            
            # 4. Add the UniqueConstraint if it doesn't exist (DML/DDL)
            print("Ensuring UniqueConstraint exists on 'graphs'...")
            with engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE graphs 
                    ADD CONSTRAINT uq_graph_query_user UNIQUE (query, user_id);
                """))
                conn.commit()
            print("✅ UniqueConstraint added.")

        except Exception as e:
            db.rollback()
            print(f"❌ Migration failed: {e}")
            if "already exists" in str(e):
                print("💡 Note: Constraint already exists, skipping.")
            else:
                raise

if __name__ == "__main__":
    migrate()
