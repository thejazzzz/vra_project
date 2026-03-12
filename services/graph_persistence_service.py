# services/graph_persistence_service.py
from sqlalchemy.dialects.postgresql import insert
from database.db import SessionLocal
from database.models.graph_model import Graph
from typing import Optional, Dict


def save_graphs(query: str, user_id: str, knowledge: dict, citation: dict, analytics: Optional[dict] = None, session_id: Optional[str] = None):
    """Insert or update the graphs for a user + query/session."""
    print("DEBUG GRAPH SAVE")
    print(f"Query: {query}")
    print(f"User: {user_id}")
    print(f"Session: {session_id}")
    
    clean_query = query.strip().lower()
    with SessionLocal() as db:
        try:
            # Use session_id as the primary conflict resolution key if available
            values = {
                "query": clean_query,
                "user_id": user_id,
                "session_id": session_id,
                "knowledge_graph": knowledge,
                "citation_graph": citation,
                "research_analytics": analytics or {}
            }
            
            stmt = insert(Graph).values(**values)
            
            # If session_id is provided, it's our most unique key
            conflict_keys = ["query", "user_id"]
            if session_id:
                # We still use the uq_graph_query_user constraint usually, 
                # but if we add a session_id constraint we'd use that.
                # For now, stick to query/user_id for the Postgres ON CONFLICT 
                # but ensure session_id is updated.
                pass

            stmt = stmt.on_conflict_do_update(
                index_elements=["query", "user_id"],
                set_={
                    "knowledge_graph": knowledge,
                    "citation_graph": citation,
                    "research_analytics": analytics or {},
                    "session_id": session_id # Ensure it's populated on update
                }
            )

            db.execute(stmt)
            db.commit()

        except Exception:
            db.rollback()
            raise


def load_graphs(query_or_session: str, user_id: str) -> Optional[Dict]:
    """Loads graphs by session_id (preferred) or query string."""
    with SessionLocal() as db:
        # ⚠️ Try lookup by session_id first (UUID)
        row = db.query(Graph).filter(
            Graph.session_id == query_or_session,
            Graph.user_id == user_id
        ).first()

        # Fallback to query lookup (legacy or manual tool trigger)
        if not row:
            clean_query = query_or_session.strip().lower()
            row = db.query(Graph).filter(
                Graph.query == clean_query,
                Graph.user_id == user_id
            ).first()

        if not row:
            return None

        return {
            "knowledge_graph": row.knowledge_graph,
            "citation_graph": row.citation_graph,
            "research_analytics": row.research_analytics or {},
            "session_id": row.session_id,
            "query": row.query
        }
