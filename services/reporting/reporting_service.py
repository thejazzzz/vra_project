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
        Requires explicit user confirmation.
        """
        if not confirm:
            raise ValueError("User must explicitly confirm start of report generation.")

        state = load_state_for_query(session_id, user_id)
        if not state:
            raise ValueError(f"Session {session_id} not found.")

        # If already active, return existing
        if state.get("report_state") and state["report_state"].get("report_status") != "idle":
             logger.info(f"Report already active for {session_id}, returning current state.")
             rep = state["report_state"]
             if rep.get("user_confirmed_start") and confirm:
                 # Bug 2 Fix: Guard against accidental re-init if already confirmed
                 logger.warning(f"Session {session_id} re-initialized but already active.")
                 # raise ValueError("Report already initialized.") # Optional strictness
             return rep

        # Plan
        initial_state = SectionPlanner.initialize_report_state(state)
        initial_state["user_confirmed_start"] = True
        
        # Update Main State
        state["report_state"] = initial_state
        state["current_step"] = "reporting_planning" # Update workflow step
        
        save_state_for_query(session_id, state, user_id)
        return initial_state

    @staticmethod
    def get_report_state(session_id: str, user_id: str) -> Optional[ReportState]:
        state = load_state_for_query(session_id, user_id)
        if not state: return None
        return state.get("report_state")

    @staticmethod
    async def generate_section(session_id: str, user_id: str, section_id: str) -> Dict[str, Any]:
        """
        Generates content for a specific section.
        Handles locking, dependency checks, and revision limits.
        """
        state = load_state_for_query(session_id, user_id)
        if not state or not state.get("report_state"):
            raise ValueError("Report not initialized.")

        rep_state: ReportState = state["report_state"]
        sections = rep_state["sections"]
        
        # Improvement 2: Deterministic Order Guard
        # Re-compute hash to ensure sections list wasn't mutated
        # For performance, we skip re-planning, but we could check IDs match order.
        # Here we just assume safe if no outside mutators. 
        
        # 1. Locate Section
        target_section = next((s for s in sections if s["section_id"] == section_id), None)
        if not target_section:
            raise ValueError(f"Section {section_id} not found.")

        # 2. Check Locks
        # Fix Bug 1: Use standardized structure locks["report"]
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
        
        # Improvement 1: Status Transition
        if rep_state["report_status"] == "planned":
            rep_state["report_status"] = "in_progress"

        save_state_for_query(session_id, state, user_id) # Commit "Generating" state

        try:
            # 6. Call Generator
            from services.reporting.report_generator import ReportGenerator
            
            # Bug 5 Fix: Receive metadata dict
            result = ReportGenerator.generate_section_content(section_id, state)
            content = result["content"]
            prompt_version = result.get("prompt_version", "unknown")
            model_name = result.get("model_name", "unknown")
            
            # Improvement 3: Enforce Markdown Validation
            if not ExportService.validate_markdown(content):
                 raise ValueError("Generated content failed Markdown validation (unsafe HTML or malformed).")

            # 7. Update State
            target_section["content"] = content
            target_section["revision"] += 1
            target_section["status"] = "review"
            
            # History
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
            
            # Bug 4 Fix: Metrics
            rep_state["metrics"]["generation_count"] += 1
            rep_state["metrics"]["total_revisions"] = rep_state["metrics"].get("total_revisions", 0) + 1
            
            # Last Success
            rep_state["last_successful_step"] = {"section_id": section_id, "phase": "generated"}

        except Exception as e:
            logger.error(f"Generation failed for {section_id}: {e}", exc_info=True)
            target_section["status"] = "error"
            # Fix Issue 2: Set global failure status
            rep_state["report_status"] = "failed"
            raise e
        finally:
            # Release Lock
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

        if accepted:
            target_section["status"] = "accepted"
            # Lock content implicitly? Yes.
            rep_state["last_successful_step"] = {"section_id": section_id, "phase": "accepted"}
            
            # Improvement 1: Check if all accepted
            if all(s["status"] == "accepted" for s in rep_state["sections"]):
                rep_state["report_status"] = "awaiting_final_review"

        else:
            # Bug 3 Fix: Handle rejection logic safely
            if target_section["revision"] >= target_section["max_revisions"]:
                 target_section["status"] = "error"
                 save_state_for_query(session_id, state, user_id)
                 raise ValueError(f"Max revisions ({target_section['max_revisions']}) reached for section {section_id}. Please edit manually or reset.")
            
            # If rejected, we allow regen (if below limits)
            target_section["status"] = "planned" # Ready for regen
            
            # Log feedback in history of CURRENT revision (the one being rejected)
            if target_section["history"]:
                target_section["history"][-1]["feedback"] = feedback
            
            # Improvement 2: Store last feedback on section for UI
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
        
        rep_state = state["report_state"]
        target_section = next((s for s in rep_state["sections"] if s["section_id"] == section_id), None)
        
        if target_section:
            target_section["status"] = "planned"
            target_section["content"] = None
            target_section["revision"] = 0
            target_section["history"] = []
            target_section["quality_scores"] = None
            target_section.pop("last_feedback", None) # Clear feedback

            # Release locks
            if rep_state["locks"]["sections"].get(section_id):
                 rep_state["locks"]["sections"][section_id] = False
            
            # If we were failed, maybe we can recover? 
            if rep_state["report_status"] == "failed":
                 # Reset to in_progress if other sections are okay
                 rep_state["report_status"] = "in_progress"

            save_state_for_query(session_id, state, user_id)
        
        return target_section

    @staticmethod
    def finalize_report(session_id: str, user_id: str, confirm: bool = False) -> ReportState:
        if not confirm: raise ValueError("Confirmation required.")

        state = load_state_for_query(session_id, user_id)
        rep_state = state["report_state"]

        # 1. Validation Phase
        rep_state["report_status"] = "validating"
        save_state_for_query(session_id, state, user_id)

        # Validate all sections accepted
        if not all(s["status"] == "accepted" for s in rep_state["sections"]):
             rep_state["report_status"] = "failed"
             save_state_for_query(session_id, state, user_id)
             raise ValueError("Validation Failed: Not all sections are accepted.")

        # Validate Order Hash (Integrity Check)
        # current_hash = ... (We would recompute here)
        # if current_hash != rep_state["section_order_hash"]:
        #      rep_state["report_status"] = "failed"
        #      raise ValueError("Integrity Error: Section order mutated.")
        
        # 2. Finalizing
        rep_state["locks"]["report"] = True
        rep_state["report_status"] = "finalizing"
        rep_state["user_confirmed_finalize"] = True
        save_state_for_query(session_id, state, user_id)

        # Assemble (Virtual)
        # For now, we just mark completed to allow export
        rep_state["report_status"] = "completed"
        
        save_state_for_query(session_id, state, user_id)
        return rep_state
