
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv(".env.local") 

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from agents.reporting_agent import reporting_agent

def verify_reporting_agent():
    logger.info("🧪 Starting Verification...")

    # Mock State
    mock_state = {
        "query": "Future of Autonomous Agents",
        "audience": "general",
        "concept_trends": {
            "trends": {
                "Agentic Works": {
                    "status": "Emerging", 
                    "growth_rate": 0.8,
                    "stability": "Volatile",
                    "total_count": 15
                }
            }
        },
        "research_gaps": [
            {
                "gap_id": "GAP_01",
                "type": "Methodological",
                "description": "Lack of standardized eval metrics.",
                "rationale": "Papers use disparate benchmarks.",
                "confidence": 0.9
            }
        ],
        "author_graph": {
            "meta": {
                "edges_present": True,
                "metrics_valid": True,
                "diversity_index": 0.75
            },
            "nodes": [
                {"id": "Dr. Smith", "influence_score": 12.5}
            ]
        },
        "selected_papers": [{"id": "P1"}, {"id": "P2"}]
    }

    try:
        result = reporting_agent.run(mock_state)
        
        if result.get("current_step") == "failed":
            logger.error(f"❌ Verification Failed: {result.get('error')}")
            return
            
        report = result.get("draft_report", "")
        
        # Checks
        checks = {
            "Header (Meta)": "Report Version:" in report,
            "Valid Metrics Flag": "Metrics Valid:" in report,
            "Exec Summary": "Executive Summary" in report,
            "Trend Section": "Trend Analysis" in report,
            "Gap Section": "Gap Analysis" in report,
            "Appendix A": "Appendix A: Evidence & Provenance" in report,
            "Footer": "Evidence Appendix" in report
        }
        
        all_passed = True
        for name, passed in checks.items():
            logger.info(f"Check '{name}': {'✅' if passed else '❌'}")
            if not passed:
                all_passed = False
                
        if all_passed:
            logger.info("✅ SUCCESS: Reporting Agent Generated Full Report.")
            print("\nPreview:\n" + report[:500] + "...")
        else:
            logger.error("❌ FAILURE: Report missing required sections.")
            print("\nFull Report:\n" + report)

    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR: {e}", exc_info=True)

if __name__ == "__main__":
    verify_reporting_agent()
