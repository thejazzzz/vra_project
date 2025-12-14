# File: services/state_service.py

from typing import Optional, cast
import logging
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
import copy

from database.db import SessionLocal
from database.models.workflow_state_model import WorkflowState
from state.state_schema import VRAState

logger = logging.getLogger(__name__)


def _get_db() -> Session:
    return SessionLocal()


def load_state_for_query(query: str, user_id: str) -> Optional[VRAState]:
    db = _get_db()
    try:
        row = (
            db.query(WorkflowState)
            .filter(WorkflowState.query == query)
            .filter(WorkflowState.user_id == user_id)
            .first()
        )

        if not row or not isinstance(row.state, dict):
            return None

        # Return a deep copy to avoid accidental mutation of ORM object state
        return cast(VRAState, copy.deepcopy(row.state))

    finally:
        db.close()


def save_state_for_query(query: str, state: VRAState, user_id: str) -> int:
    db = _get_db()
    try:
        stmt = (
            insert(WorkflowState)
            .values(
                query=query,
                user_id=user_id,
                state=dict(state)
            )
            .on_conflict_do_update(
                index_elements=["query", "user_id"],
                set_={"state": dict(state)}  # FIXED
            )
            .returning(WorkflowState.id)
        )

        result = db.execute(stmt)
        db.commit()
        return result.scalar_one()

    except Exception:
        db.rollback()
        logger.exception("Failed to persist workflow state.")
        raise

    finally:
        db.close()
