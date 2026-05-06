# File: services/cleanup_service.py
import logging
from sqlalchemy.orm import Session
from database.models.workflow_state_model import WorkflowState
from database.models.auth_models import ResearchSession, AuditLog
from services.graph_persistence_service import delete_graphs_for_session
from services.infrastructure.redis_pool import get_redis_client
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def hard_delete_session(session_id: str, user_id: str, db: Session) -> bool:
    """
    Executes a hard deletion of all data associated with a research session
    in a single database transaction.
    """
    logger.info(f"Initiating hard delete for session {session_id} by user {user_id}")
    
    try:
        with db.begin_nested():
            # 1. Delete associated graphs
            delete_graphs_for_session(session_id, user_id, db=db)
            
            # 2. Delete WorkflowState
            db.query(WorkflowState).filter(
                WorkflowState.query == session_id,
                WorkflowState.user_id == user_id
            ).delete()
            
            # 3. Delete ResearchSession
            session_row = db.query(ResearchSession).filter(
                ResearchSession.session_id == session_id,
                ResearchSession.user_id == user_id
            ).first()
            
            if session_row:
                db.delete(session_row)
                
        # Commit the transaction
        db.commit()
        
        # Clear Redis artifacts
        try:
            redis_client = get_redis_client()
            if redis_client:
                # We could delete section caches if we knew the keys, but they use a hash.
                # However, they expire automatically (TTL=86400).
                # We can delete the job owner key to invalidate any background Celery task checks.
                redis_client.delete(f"job_owner:{session_id}")
                # We can't easily bulk-delete section_cache keys by prefix without SCAN,
                # but the TTL is fine. We will just let them expire.
        except Exception as e:
            logger.warning(f"Failed to clear Redis caches for {session_id}: {e}")
            
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Hard delete failed for session {session_id}: {e}", exc_info=True)
        raise
