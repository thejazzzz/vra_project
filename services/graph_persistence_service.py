# services/graph_persistence_service.py
from sqlalchemy.dialects.postgresql import insert
from database.db import SessionLocal
from database.models.graph_model import Graph
from typing import Optional, Dict


def save_graphs(query: str, user_id: str, knowledge: dict, citation: dict):
    """Insert or update the graphs for a user + query."""
    with SessionLocal() as db:
        try:
            stmt = insert(Graph).values(
                query=query,
                user_id=user_id,
                knowledge_graph=knowledge,
                citation_graph=citation,
            ).on_conflict_do_update(
                index_elements=["query", "user_id"],
                set_={
                    "knowledge_graph": knowledge,
                    "citation_graph": citation,
                }
            )

            db.execute(stmt)
            db.commit()

        except Exception:
            db.rollback()
            raise


def load_graphs(query: str, user_id: str) -> Optional[Dict]:
    with SessionLocal() as db:
        row = db.query(Graph).filter(
            Graph.query == query,
            Graph.user_id == user_id
        ).first()

        if not row:
            return None

        return {
            "knowledge_graph": row.knowledge_graph,
            "citation_graph": row.citation_graph,
        }
