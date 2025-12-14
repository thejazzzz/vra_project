# agents/reporting_agent.py
import logging
from typing import Dict, Any
from services.analysis_service import generate_report_content

logger = logging.getLogger(__name__)

class ReportingAgent:
    """
    Synthesizes the global analysis and paper summaries into a final research report.
    """

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("✍️ Reporting Agent: Generating final report...")

        query = state.get("query", "")
        analysis = state.get("global_analysis", {})
        summary = analysis.get("summary", "No summary available.")
        concepts = analysis.get("key_concepts", [])
        
        # Build prompt
        prompt = (
            f"Research Query: {query}\n\n"
            f"Global Analysis Summary: {summary}\n"
            f"Key Concepts: {', '.join(concepts)}\n\n"
            "Please write a structured research report in Markdown format. "
            "Include an Introduction, Key Findings section, and a Conclusion."
        )

        try:
            report_text = generate_report_content(prompt)
            state["draft_report"] = report_text
            state["current_step"] = "awaiting_final_review"
            logger.info("✅ Report generated successfully.")
        except Exception as e:
            logger.error(f"Reporting failed: {e}")
            state["error"] = "Report generation failed."
            state["current_step"] = "completed"

        return state

reporting_agent = ReportingAgent()
