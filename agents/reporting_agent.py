# agents/reporting_agent.py
import logging
import os
from typing import Dict, Any

from services.reporting.section_planner import SectionPlanner

logger = logging.getLogger(__name__)

class ReportingAgent:
    """
    Synthesizes global analysis, structured summaries, gaps, trends, and graphs
    into a final research report.
    Phase 3 Enhanced: Uses Deterministic Section Planning and Chunked Generation.
    """

    def __init__(self):
        pass

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("✍️ Reporting Agent: Planning report structure (Phase 3 Interactive)...")

        try:
            # Plan the report (Fast)
            # We used to generate completely here, but that takes too long (~10 mins).
            # Now we just initialize the state and let the user drive generation in the dashboard.
            initial_rep_state = SectionPlanner.initialize_report_state(state)
            
            state["report_state"] = initial_rep_state
            
            # Use specific step to signal UI to show "Start Report"
            state["current_step"] = "awaiting_report_start"
            logger.info("✅ Report planned successfully. Waiting for user start.")
            
        except Exception as e:
            logger.error(f"Reporting planning failed: {e}", exc_info=True)
            state["error"] = f"Report planning failed: {str(e)}"
            state["current_step"] = "failed"
        
        return state

reporting_agent = ReportingAgent()
