# scripts/standardize_graph_queries.py
import os
import sys
import logging
from sqlalchemy import text
from datetime import datetime

# Adjust path to allow importing from project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import engine, SessionLocal
from database.models.graph_model import Graph
from database.models.auth_models import ResearchSession
from database.models.workflow_state_model import WorkflowState

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("migration")

def migrate():
    logger.info("🚀 Starting Advanced Data Migration (Session-ID Backfill)...")
    
    with SessionLocal() as db:
        try:
            # --- 1. RESEARCH SESSIONS (Normalize first) ---
            logger.info("--- Phase 1: Normalizing Research Sessions ---")
            sessions = db.query(ResearchSession).all()
            session_lookup = {} # (query_lower, user_id) -> session_id
            for s in sessions:
                old_q = s.query
                new_q = old_q.strip().lower()
                if old_q != new_q:
                    logger.info(f"Standardizing Session {s.session_id}: '{old_q}' -> '{new_q}'")
                    s.query = new_q
                
                key = (new_q, s.user_id)
                session_lookup[key] = s.session_id
            
            # --- 2. WORKFLOW STATES ---
            logger.info("--- Phase 2: Normalizing Workflow States ---")
            states = db.query(WorkflowState).all()
            for ws in states:
                old_q = ws.query
                new_q = old_q.strip().lower()
                if old_q != new_q:
                    logger.info(f"Standardizing State for User {ws.user_id}: '{old_q}' -> '{new_q}'")
                    ws.query = new_q

            # --- 3. GRAPHS (Backfill session_id & Deduplication) ---
            logger.info("--- Phase 3: Backfilling session_id & Deduplicating Graphs ---")
            # Order by newest first so we keep the most recent graph in case of duplicates
            all_graphs = db.query(Graph).order_by(Graph.updated_at.desc()).all()
            
            seen = {} # (query_lower, user_id) -> graph_id
            to_delete = []
            
            for g in all_graphs:
                clean_q = g.query.strip().lower()
                key = (clean_q, g.user_id)
                
                if key in seen:
                    logger.warning(f"Duplicate Graph! Keeping ID {seen[key]}, deleting older ID {g.id} for '{clean_q}'")
                    to_delete.append(g)
                    continue
                
                seen[key] = g.id
                
                # Update query casing
                if g.query != clean_q:
                    logger.info(f"Standardizing Query for Graph {g.id}: '{g.query}' -> '{clean_q}'")
                    g.query = clean_q
                
                # Backfill session_id if missing
                if not g.session_id:
                    if key in session_lookup:
                        s_id = session_lookup[key]
                        logger.info(f"Backfilling session_id {s_id} for Graph {g.id} (query: '{clean_q}')")
                        g.session_id = s_id
                    else:
                        logger.warning(f"Could not find matching session for Graph {g.id} (query: '{clean_q}')")

            for g in to_delete:
                db.delete(g)

            db.commit()
            logger.info("✅ Data successfully normalized and session_id backfilled.")
            
            # --- 4. DATABASE CONSTRAINTS ---
            logger.info("--- Phase 4: Ensuring Database Constraints ---")
            with engine.connect() as conn:
                # Add UniqueConstraint to graphs if missing
                try:
                    conn.execute(text("""
                        ALTER TABLE graphs 
                        ADD CONSTRAINT uq_graph_query_user UNIQUE (query, user_id);
                    """))
                    conn.commit()
                    logger.info("✅ UniqueConstraint 'uq_graph_query_user' ensured.")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        logger.info("💡 Note: Constraint 'uq_graph_query_user' already exists.")
                    else:
                        logger.error(f"⚠️ Warning: Could not add constraint uq_graph_query_user: {e}")

                # Add session_id index
                try:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_graphs_session_id ON graphs (session_id);"))
                    conn.commit()
                    logger.info("✅ Index 'ix_graphs_session_id' ensured.")
                except Exception as e:
                     logger.error(f"⚠️ Warning: Could not create index on session_id: {e}")

            # --- 5. SUMMARY ---
            logger.info("--- Phase 5: DB State Summary ---")
            total_g = db.query(Graph).count()
            total_s = db.query(ResearchSession).count()
            g_with_sid = db.query(Graph).filter(Graph.session_id != None).count()
            
            logger.info(f"Summary: {total_g} Graphs total, {g_with_sid} linked with session_id.")
            logger.info(f"Summary: {total_s} Sessions total.")

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Migration FAILED: {type(e).__name__}: {e}")
            raise

if __name__ == "__main__":
    migrate()
