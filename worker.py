# File: worker.py
import os
import asyncio
from celery import Celery
import logging

logging.basicConfig(level=logging.INFO)

from services.reporting.report_generator import ReportGenerator
from services.state_service import load_state_for_query, save_state_for_query

# Configure Celery
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Apply SSL config to the URL directly before initialization (Celery requirement)
if redis_url.startswith("rediss://") and "ssl_cert_reqs" not in redis_url:
    if "?" in redis_url:
        redis_url += "&ssl_cert_reqs=CERT_NONE"
    else:
        redis_url += "?ssl_cert_reqs=CERT_NONE"

celery_app = Celery("vra_worker", broker=redis_url, backend=redis_url)

# Add reliability configurations for long-running AI tasks
celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
)

logger = logging.getLogger(__name__)

from celery.signals import worker_shutting_down

@worker_shutting_down.connect
def on_worker_shutdown(**kwargs):
    logger.info("Worker is shutting down gracefully. Allowing active tasks to finish...")

@celery_app.task(bind=True, name="generate_report_task", soft_time_limit=900, time_limit=1200)
def generate_report_task(self, session_id: str, user_id: str):
    logger.info(f"[Task {self.request.id}] Started generating report for session {session_id}")
    state = load_state_for_query(session_id, user_id)
    if not state:
        return {"status": "error", "message": "State not found"}
        
    try:
        # Phase 11 & 12: The Report Generator will handle Phases 1-5 in parallel.
        generator = ReportGenerator()
        
        # Explicit Event Loop Management for Celery Stability
        final_report = asyncio.run(generator.generate_report_async(state))
        
        # Save the completed report
        if "report_state" not in state:
            state["report_state"] = {}
        rep_state = state["report_state"]
        
        if "sections" not in rep_state:
            rep_state["sections"] = []
            
        rep_state["completed_report"] = final_report
        rep_state["report_status"] = "completed"
        
        save_state_for_query(session_id, state, user_id)
        return {"status": "success", "session_id": session_id}
        
    except Exception as e:
        import celery.exceptions
        if isinstance(e, celery.exceptions.SoftTimeLimitExceeded):
            logger.error(f"[Task {self.request.id}] Soft timeout for session {session_id}: {e}")
        else:
            logger.error(f"[Task {self.request.id}] Failed for session {session_id}: {e}", exc_info=True)
            
        if "report_state" not in state:
            state["report_state"] = {}
        rep_state = state["report_state"]
        
        rep_state["report_status"] = "failed"
        rep_state["error"] = str(e)  # Keep exact error in internal state
        save_state_for_query(session_id, state, user_id)
        
        return {"status": "error", "message": "An internal error occurred during report generation."}
