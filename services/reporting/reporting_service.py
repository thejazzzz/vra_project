#File: services/reporting/reporting_services.py
from typing import Dict, Any, List, Optional, Tuple
import logging
import datetime
import hashlib
import json
import uuid

from state.state_schema import ReportState, ReportSectionState, SectionHistory, VRAState
from services.state_service import load_state_for_query, save_state_for_query
from services.reporting.section_planner import SectionPlanner
# from services.reporting.report_generator import ReportGenerator # Circular? We will inject or import inside methods.
from services.reporting.export_service import ExportService

logger = logging.getLogger(__name__)

class InteractiveReportingService:
    """
    Orchestrates the interactive, stateful reporting workflow.
    Manages locking, generation, review, and finalization.
    """

    @staticmethod
    def initialize_report(session_id: str, user_id: str, confirm: bool = False) -> Dict[str, Any]:
        """
        Initializes the report structure (PLANNING phase).
        Uses DATABASE LOCKING to prevent race conditions.
        """
        if not confirm:
            raise ValueError("User must explicitly confirm start of report generation.")

        # Use direct DB session for atomic check-and-set
        from database.db import SessionLocal
        from database.models.workflow_state_model import WorkflowState
        from sqlalchemy.orm.attributes import flag_modified
        import copy

        db = SessionLocal()
        try:
            # Select for update to lock the row
            row = db.query(WorkflowState).filter(
                WorkflowState.query == session_id,
                WorkflowState.user_id == user_id
            ).with_for_update().first()

            if not row or not row.state:
                raise ValueError(f"Session {session_id} not found.")

            state = copy.deepcopy(row.state)
            
            # If already active, return existing
            if state.get("report_state") and state["report_state"].get("report_status") != "idle":
                 logger.info(f"Report already active for {session_id}, returning current state.")
                 rep = state["report_state"]
                 if rep.get("user_confirmed_start") and confirm:
                     logger.warning(f"Session {session_id} re-initialized but already active.")
                 db.commit() # Release lock
                 return rep

            # Plan
            initial_state = SectionPlanner.initialize_report_state(state)
            initial_state["user_confirmed_start"] = True
            
            # Update Main State
            state["report_state"] = initial_state
            state["current_step"] = "reporting_planning" 
            
            # Commit update
            row.state = state
            flag_modified(row, "state")
            db.commit()
            return initial_state
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @staticmethod
    def get_report_state(session_id: str, user_id: str) -> Optional[ReportState]:
        state = load_state_for_query(session_id, user_id)
        if not state: return None
        return state.get("report_state")

    @staticmethod
    def generate_section(session_id: str, user_id: str, section_id: str) -> Dict[str, Any]:
        """
        Generates content for a specific section.
        Synchronous execution (run in threadpool via FastAPI).
        """
        state = load_state_for_query(session_id, user_id)
        if not state or not state.get("report_state"):
            raise ValueError("Report not initialized.")

        rep_state: ReportState = state["report_state"]
        sections = rep_state["sections"]
        
        # 1. Locate Section
        target_section = next((s for s in sections if s["section_id"] == section_id), None)
        if not target_section:
            raise ValueError(f"Section {section_id} not found.")

        # 2. Check Locks
        if rep_state["locks"].get("report"):
            raise ValueError("Report is locked (finalizing/exporting).")
        
        # Check if ANY other section is generating
        generating_sections = [s for s in sections if s["status"] == "generating"]
        for gs in generating_sections:
            if gs["section_id"] != section_id:
                 raise ValueError(f"Another section ({gs['section_id']}) is currently generating. Please wait.")

        # 3. Check Dependencies
        for dep_id in target_section["depends_on"]:
             dep_sec = next((s for s in sections if s["section_id"] == dep_id), None)
             if not dep_sec or dep_sec["status"] != "accepted":
                  raise ValueError(f"Dependency '{dep_id}' is not yet accepted.")

        # 4. Check Revisions
        if target_section["revision"] >= target_section["max_revisions"]:
             raise ValueError(f"Max revisions ({target_section['max_revisions']}) reached for section {section_id}.")

        # 5. Acquire Lock & Set Status
        rep_state["locks"]["sections"][section_id] = True
        target_section["status"] = "generating"
        
        if rep_state["report_status"] == "planned":
            rep_state["report_status"] = "in_progress"

        save_state_for_query(session_id, state, user_id) 

        try:
            # 6. Call Generator (Sync)
            from services.reporting.report_generator import ReportGenerator
            
            result = ReportGenerator.generate_section_content(section_id, state)
            content = result["content"]
            prompt_version = result.get("prompt_version", "unknown")
            model_name = result.get("model_name", "unknown")
            
            if not ExportService.validate_markdown(content):
                 raise ValueError("Generated content failed Markdown validation (unsafe HTML or malformed).")

            # 7. Update State
            target_section["content"] = content
            target_section["revision"] += 1
            target_section["status"] = "review"
            
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            history_entry: SectionHistory = {
                "revision": target_section["revision"],
                "content": content,
                "content_hash": content_hash,
                "feedback": None,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "prompt_version": prompt_version,
                "model_name": model_name
            }
            target_section["history"].append(history_entry)
            
            rep_state["metrics"]["generation_count"] += 1
            rep_state["metrics"]["total_revisions"] = rep_state["metrics"].get("total_revisions", 0) + 1
            
            rep_state["last_successful_step"] = {"section_id": section_id, "phase": "generated"}

        except Exception as e:
            logger.error(f"Generation failed for {section_id}: {e}", exc_info=True)
            target_section["status"] = "error"
            rep_state["report_status"] = "failed"
            raise e
        finally:
            rep_state["locks"]["sections"][section_id] = False
            save_state_for_query(session_id, state, user_id)

        return target_section

    @staticmethod
    def submit_review(session_id: str, user_id: str, section_id: str, accepted: bool, feedback: str = None) -> Dict[str, Any]:
        state = load_state_for_query(session_id, user_id)
        if not state or not state.get("report_state"): raise ValueError("State not found")
        
        rep_state = state["report_state"]
        target_section = next((s for s in rep_state["sections"] if s["section_id"] == section_id), None)
        if not target_section: raise ValueError("Section not found")

        # Guard: Check status is review
        if target_section["status"] != "review":
             # We might allow 'error' to be reviewed if content exists? 
             # Or if user is retrying review. But typically submit_review means approving generated content.
             # Strict:
             logger.warning(f"Attempted to review section {section_id} in status {target_section['status']}")
             # raise ValueError(f"Section {section_id} is not in review status (current: {target_section['status']})") 
             # Allow idempotency if already accepted?
             if target_section["status"] == "accepted" and accepted:
                 return target_section
             if target_section["status"] == "planned" and not accepted:
                 return target_section
             
             # If status is generating or error, maybe block?
             if target_section["status"] == "generating":
                 raise ValueError("Cannot review while generating.")
             # If error, reject the review attempt - user should reset section first
             if target_section["status"] == "error":
                 raise ValueError("Cannot review section in error state. Please reset the section first.")        

        if accepted:
            target_section["status"] = "accepted"
            rep_state["last_successful_step"] = {"section_id": section_id, "phase": "accepted"}
            
            if all(s["status"] == "accepted" for s in rep_state["sections"]):
                rep_state["report_status"] = "awaiting_final_review"

        else:
            if target_section["revision"] >= target_section["max_revisions"]:
                 target_section["status"] = "error"
                 save_state_for_query(session_id, state, user_id)
                 raise ValueError(f"Max revisions ({target_section['max_revisions']}) reached for section {section_id}. Please edit manually or reset.")
            
            target_section["status"] = "planned" 
            
            if target_section["history"]:
                target_section["history"][-1]["feedback"] = feedback
            
            target_section["last_feedback"] = feedback

        save_state_for_query(session_id, state, user_id)
        return target_section

    @staticmethod
    def reset_section(session_id: str, user_id: str, section_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Hard reset of a section. Admin/Safety hatch.
        """
        if not force:
             raise ValueError("Force=True required to reset section.")

        state = load_state_for_query(session_id, user_id)
        if not state: raise ValueError("State not found")
        if not state.get("report_state"): raise ValueError("Report state not initialized")

        rep_state = state["report_state"]
        target_section = next((s for s in rep_state["sections"] if s["section_id"] == section_id), None)
        
        if not target_section:
             raise ValueError(f"Section {section_id} not found.")

        target_section["status"] = "planned"
        target_section["content"] = None
        target_section["revision"] = 0
        target_section["history"] = []
        target_section["quality_scores"] = None
        target_section.pop("last_feedback", None) 

        # Release locks
        if rep_state["locks"]["sections"].get(section_id):
                rep_state["locks"]["sections"][section_id] = False
        
        # Recover from failed state ONLY if no other sections are failed
        # and checking if we should be in_progress
        if rep_state["report_status"] == "failed":
                other_failed = any(
                    s["status"] == "error" 
                    for s in rep_state["sections"] 
                    if s["section_id"] != section_id
                )
                if not other_failed:
                    rep_state["report_status"] = "in_progress"

        save_state_for_query(session_id, state, user_id)
        return target_section

    @staticmethod
    def finalize_report(session_id: str, user_id: str, confirm: bool = False) -> ReportState:
        if not confirm: raise ValueError("Confirmation required.")

        state = load_state_for_query(session_id, user_id)
        if not state or not state.get("report_state"):
             raise ValueError("Report state not valid or not initialized.")

        rep_state = state["report_state"]

        # 1. Validation Phase
        rep_state["report_status"] = "validating"
        save_state_for_query(session_id, state, user_id)

        # Validate all sections accepted
        if not all(s["status"] == "accepted" for s in rep_state["sections"]):
             rep_state["report_status"] = "failed"
             save_state_for_query(session_id, state, user_id)
             raise ValueError("Validation Failed: Not all sections are accepted.")
        
        # 2. Finalizing
        rep_state["locks"]["report"] = True
        rep_state["report_status"] = "finalizing"
        rep_state["user_confirmed_finalize"] = True
        save_state_for_query(session_id, state, user_id)

        # Assemble (Virtual)
        rep_state["report_status"] = "completed"
        
        save_state_for_query(session_id, state, user_id)
        return rep_state
