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
    
    if not session_id:
        raise ValueError("session_id is required to save graphs")

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
            # Enforced ON CONFLICT utilizing the uq_graph_session unique constraint
            stmt = stmt.on_conflict_do_update(
                index_elements=["session_id"],
                set_={
                    "knowledge_graph": knowledge,
                    "citation_graph": citation,
                    "research_analytics": analytics or {},
                    "query": clean_query # Optional update in case query diverges per session
                }
            )

            db.execute(stmt)
            db.commit()

        except Exception:
            db.rollback()
            raise


def load_graphs(query_or_session: str, user_id: str) -> Optional[Dict]:
    """Loads graphs strictly by session_id."""
    with SessionLocal() as db:
        row = db.query(Graph).filter(
            Graph.session_id == query_or_session,
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

def delete_graphs_for_session(session_id: str, user_id: str, db=None) -> bool:
    """Deletes the graphs associated with a session. Uses provided DB session if available."""
    
    def _delete(session):
        row = session.query(Graph).filter(
            Graph.session_id == session_id,
            Graph.user_id == user_id
        ).first()
        if row:
            session.delete(row)
            return True
        return False

    if db:
        return _delete(db)
    
    with SessionLocal() as session:
        try:
            result = _delete(session)
            session.commit()
            return result
        except Exception:
            session.rollback()
            raise
