# File: services/state_service.py
from typing import Optional, cast
import logging

from sqlalchemy.orm import Session

from database.db import SessionLocal
from database.models.workflow_state_model import WorkflowState
from state.state_schema import VRAState

logger = logging.getLogger(__name__)


def _get_db() -> Session:
    return SessionLocal()


def load_state_for_query(query: str) -> Optional[VRAState]:
    """
    Load the most recent workflow state for a given query.
    (Later you can add user_id filtering too.)
    """
    db = _get_db()
    try:
        row: Optional[WorkflowState] = (
            db.query(WorkflowState)
            .filter(WorkflowState.query == query)
            .order_by(WorkflowState.id.desc())
            .first()
        )
        if not row:
            return None

        if not isinstance(row.state, dict):
            logger.warning("WorkflowState.state is not a dict; ignoring row.")
            return None

        # cast to VRAState for type checkers
        return cast(VRAState, row.state)
    finally:
        db.close()


def save_state_for_query(
    query: str,
    state: VRAState,
    user_id: Optional[str] = None,
) -> int:
    """
    Save (or update) the workflow state for a given query.

    Current behavior:
      - If a row exists for this query, update its state.
      - Otherwise, create a new row.
    """
    db = _get_db()
    try:
        row: Optional[WorkflowState] = (
            db.query(WorkflowState)
            .filter(WorkflowState.query == query)
            .order_by(WorkflowState.id.desc())
            .first()
        )

        if row:
            row.state = dict(state)  # JSON column accepts dict
            if user_id is not None:
                row.user_id = user_id
        else:
            row = WorkflowState(
                query=query,
                user_id=user_id,
                state=dict(state),
            )
            db.add(row)

        db.commit()
        db.refresh(row)
        return row.id
    except Exception:
        db.rollback()
        logger.exception("Failed to persist workflow state.")
        raise
    finally:
        db.close()
