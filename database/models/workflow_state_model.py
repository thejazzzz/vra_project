# File: database/models/workflow_state_model.py
from sqlalchemy import Column, Integer, String, JSON, Text, DateTime, func
from database.db import Base


class WorkflowState(Base):
    """
    Persisted workflow state for the VRA planner.

    For now:
      - keyed primarily by `query`
      - `user_id` is nullable but ready for multi-user support
    """
    __tablename__ = "workflow_states"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # For future multi-user SaaS: you can later wire this to your auth system
    user_id = Column(String(255), nullable=True, index=True)

    # Logical key for this workflow; right now one workflow per query
    query = Column(Text, nullable=False, unique=True)
    # Full VRAState stored as JSON
    state = Column(JSON, nullable=False)

    # Timestamps (optional but handy for debugging / ordering)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
