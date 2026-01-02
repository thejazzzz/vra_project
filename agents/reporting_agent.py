# agents/reporting_agent.py
import logging
import os
from typing import Dict, Any

# Import the new Generator
from services.reporting.report_generator import ReportGenerator

logger = logging.getLogger(__name__)

class ReportingAgent:
    """
    Synthesizes global analysis, structured summaries, gaps, trends, and graphs
    into a final research report.
    Phase 3 Enhanced: Uses Deterministic Section Planning and Chunked Generation.
    """

    def __init__(self):
        self.generator = ReportGenerator()

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("✍️ Reporting Agent: Generating final report (Phase 3 Arch)...")

        try:
            # The ReportGenerator handles planning, context building, and generation.
            final_report = self.generator.generate_report(state)
            
            state["draft_report"] = final_report
            state["current_step"] = "awaiting_final_review"
            logger.info("✅ Report generated successfully (Phase 3).")
            
        except Exception as e:
            logger.error(f"Reporting failed: {e}", exc_info=True)
            state["error"] = f"Report generation failed: {str(e)}"
            state["current_step"] = "failed"
        
        return state

reporting_agent = ReportingAgent()
