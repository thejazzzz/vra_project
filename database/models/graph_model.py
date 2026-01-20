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
    research_analytics = Column(JSON, nullable=True) # Phase 2: Conflicts, Gaps, Novelty

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class UserGraphOverride(Base):
    """
    Phase 3: User Learning Loop.
    Persist user corrections to auto-improve future graphs.
    """
    __tablename__ = "user_graph_overrides"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    
    source = Column(String(255), nullable=False)
    target = Column(String(255), nullable=False)
    relation = Column(String(255), nullable=True) # Optional if removing any link
    
    # Action
    action = Column(String(50), nullable=False) # "reject_edge", "confirm_edge", "add_edge"
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
