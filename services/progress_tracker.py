# services/progress_tracker.py
import asyncio
import logging
from enum import Enum
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)

class ResearchPhase(str, Enum):
    INITIALIZING = "INITIALIZING"
    EXPANDING_QUERIES = "EXPANDING_QUERIES"
    FETCHING_PAPERS = "FETCHING_PAPERS"
    MERGING_RESULTS = "MERGING_RESULTS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ResearchProgress:
    def __init__(self, task_id: str, user_id: Optional[str] = None):
        self.task_id = task_id
        self.user_id = user_id
        self.phase = ResearchPhase.INITIALIZING
        self.queries_total = 0
        self.queries_completed = 0
        self.queries_failed = 0
        self.papers_found = 0
        self.last_updated = datetime.now()
        self.error: Optional[str] = None
        self._lock = threading.Lock()

    _UPDATABLE_FIELDS = {'phase', 'queries_total', 'queries_completed', 
                         'queries_failed', 'papers_found', 'error'}

    def update(self, **kwargs):
        with self._lock:
            for key, value in kwargs.items():
                if key in self._UPDATABLE_FIELDS:
                    setattr(self, key, value)
            self.last_updated = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "task_id": self.task_id,
                "phase": self.phase.value,
                "queries_total": self.queries_total,
                "queries_completed": self.queries_completed,
                "queries_failed": self.queries_failed,
                "papers_found": self.papers_found,
                "error": self.error,
                "last_updated": self.last_updated.isoformat()
            }

class ProgressTracker:
    _instances: Dict[str, ResearchProgress] = {}
    _lock = threading.Lock()
    
    # Simple TTL cleanup: any task older than 1 hour is removed
    TTL = timedelta(hours=1)

    @classmethod
    def start_task(cls, task_id: str, user_id: Optional[str] = None, overwrite: bool = False) -> ResearchProgress:
        cls._cleanup()
        with cls._lock:
            # Check for existence under lock
            if task_id in cls._instances:
                if not overwrite:
                    logger.warning(f"Task {task_id} already exists. Returning existing tracker.")
                    return cls._instances[task_id]
                # If overwrite is True, we replace it.
            
            progress = ResearchProgress(task_id, user_id)
            cls._instances[task_id] = progress
            return progress

    @classmethod
    def get_progress(cls, task_id: str) -> Optional[Dict[str, Any]]:
        with cls._lock:
            progress = cls._instances.get(task_id)
            if progress:
                return progress.to_dict()
            return None

    @classmethod
    def get_task_owner(cls, task_id: str) -> Optional[str]:
        with cls._lock:
            progress = cls._instances.get(task_id)
            if progress:
                return progress.user_id
            return None

    @classmethod
    def update_task(cls, task_id: str, **kwargs):
        # Optimistic retrieval without main lock for update
        # ResearchProgress has its own lock
        progress = cls._instances.get(task_id)
        if progress:
            progress.update(**kwargs)

    @classmethod
    def _cleanup(cls):
        # remove old tasks safely avoiding race conditions
        now = datetime.now()
        
        # 1. Snapshot items under main lock
        with cls._lock:
            snapshot = list(cls._instances.items())
            
        expired_items = []
        
        # 2. Check expiration using per-instance locks
        for tid, prog in snapshot:
            with prog._lock:
                if now - prog.last_updated > cls.TTL:
                    expired_items.append((tid, prog))
        
        # 3. Remove expired under main lock with IDENTITY CHECK
        if expired_items:
            with cls._lock:
                for tid, prog in expired_items:
                    # Prevent TOCTOU: only delete if it's still the SAME object
                    if cls._instances.get(tid) is prog:
                        cls._instances.pop(tid, None)
