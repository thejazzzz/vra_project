# database/models/memory_model.py
from sqlalchemy import Column, Integer, String, JSON, DateTime, Float, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from database.db import Base
import enum

class TrendState(enum.Enum):
    EMERGING = "emerging"
    STABLE = "stable"
    DECLINING = "declining"
    REEMERGING = "reemerging" # Revived topic

class GlobalConceptStats(Base):
    """
    Phase 4: Longitudinal Concept Memory.
    Tracks how often a concept appears across ALL approved runs.
    """
    __tablename__ = "global_concept_stats"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    concept_id = Column(String(255), unique=True, nullable=False, index=True) # Canonical ID
    
    first_seen = Column(DateTime(timezone=True), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=False)
    
    run_count = Column(Integer, default=1)
    weighted_frequency = Column(Float, default=1.0) # sum(confidence)
    
    trend_state = Column(Enum(TrendState), default=TrendState.EMERGING)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class GlobalEdgeStats(Base):
    """
    Phase 4: Longitudinal Relation Memory.
    Used for Novelty Decay and Conflict Auditing.
    """
    __tablename__ = "global_edge_stats"
    __table_args__ = (
        UniqueConstraint('source', 'target', 'relation', name='uq_edge_relation'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Composite Key logically (source, target, relation)
    source = Column(String(255), nullable=False, index=True)
    target = Column(String(255), nullable=False, index=True)
    relation = Column(String(255), nullable=False, index=True) # Added Index
    
    first_seen = Column(DateTime(timezone=True), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=False)
    
    run_count = Column(Integer, default=1)
    weighted_frequency = Column(Float, default=1.0) # sum(confidence)
    
    # Contestation Audit
    contested_count = Column(Integer, default=0) # Number of user rejections
    contested_by_users = Column(JSON, default=list) # List of user_ids who rejected
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

