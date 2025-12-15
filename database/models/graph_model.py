# database/models/graph_model.py
from sqlalchemy import Column, Integer, String, JSON, DateTime, func, UniqueConstraint
from database.db import Base

class Graph(Base):
    __tablename__ = "graphs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    query = Column(String(500), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)

    knowledge_graph = Column(JSON, nullable=True)
    citation_graph = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("query", "user_id", name="uq_graph_query_user"),
    )
