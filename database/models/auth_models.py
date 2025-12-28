from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database.db import Base
from datetime import datetime
import enum

class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    RESEARCHER = "RESEARCHER"
    ADMIN = "ADMIN"

class SessionStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    AWAITING_INPUT = "awaiting_input"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True) # UUID or Auth0 ID
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.STUDENT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships 
    sessions = relationship("ResearchSession", back_populates="owner")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

class ResearchSession(Base):
    __tablename__ = "research_sessions"

    session_id = Column(String, primary_key=True, index=True) # Query hash or UUID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    query = Column(String, nullable=False)
    status = Column(Enum(SessionStatus, values_callable=lambda x: [e.value for e in x]), default=SessionStatus.RUNNING)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="sessions")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, index=True) # UUID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False) # e.g. "APPROVE_PAPER", "TRIGGER_REPORT"
    target_id = Column(String, nullable=True) # e.g. session_id or paper_id
    payload = Column(String, nullable=True) # JSON string of details
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String, nullable=True)

    # Relationships
    user = relationship("User")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, index=True) # UUID
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked = Column(Boolean, default=False)
    family_id = Column(String, nullable=True, index=True) # For rotation families

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
