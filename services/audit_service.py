from sqlalchemy.orm import Session
from database.models.auth_models import AuditLog
import uuid
import json
from datetime import datetime, timezone

def log_action(db: Session, user_id: str, action: str, target_id: str = None, payload: dict = None, ip_address: str = None):
    """
    Creates an immutable audit log entry.
    """
    log_entry = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action=action,
        target_id=target_id,
        payload=json.dumps(payload) if payload else None,
        ip_address=ip_address,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
