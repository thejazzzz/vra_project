# File: database/models/workflow_state_model.py
from sqlalchemy import Column, Integer, String, JSON, Text, DateTime, UniqueConstraint, func
from database.db import Base

class WorkflowState(Base):
    __tablename__ = "workflow_states"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    user_id = Column(String(255), nullable=False, index=True)

    query = Column(String(500), nullable=False)
    state = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("query", "user_id", name="uq_query_user"),
    )
