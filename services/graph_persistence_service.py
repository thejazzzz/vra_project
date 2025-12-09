#services/graph_persistence_service.py
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from database.db import SessionLocal
from database.models.graph_model import Graph

def save_graphs(query: str, user_id: str, knowledge: dict, citation: dict):
    db: Session = SessionLocal()
    try:
        stmt = insert(Graph).values(
            query=query,
            user_id=user_id,
            knowledge_graph=knowledge,
            citation_graph=citation
        ).on_conflict_do_update(
            index_elements=["query", "user_id"],
            set_={
                "knowledge_graph": knowledge,
                "citation_graph": citation
            }
        )
        db.execute(stmt)
        db.commit()
    finally:
        db.close()


def load_graphs(query: str, user_id: str) -> dict | None:
    db: Session = SessionLocal()
    try:
        row = db.query(Graph).filter(Graph.query == query).filter(Graph.user_id == user_id).first()
        return {
            "knowledge_graph": row.knowledge_graph,
            "citation_graph": row.citation_graph,
        } if row else None
    finally:
        db.close()
