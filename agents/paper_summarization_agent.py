# agents/paper_summarization_agent.py
import logging
from services.structured_llm import generate_structured_json

logger = logging.getLogger(__name__)

class PaperSummarizationAgent:
    name = "paper_summarization_agent"

    def run(self, state):
        logger.info("📄 Summarizing paper content (Reliable Mode)...")
        papers = state.get("selected_papers", [])
        summaries = {}

        # Schema Validation Set
        REQUIRED_KEYS = {
            "problem", "method", "results", 
            "limitations", "future_work", "concepts"
        }

        for paper in papers:
            pid = paper.get("canonical_id")
            if not pid:
                continue

            title = paper.get("title", "Unknown Title")
            abstract = paper.get("abstract", "No abstract available.")
            
            prompt = f"""
            Analyze the following research paper based on its title and abstract.
            
            Paper Title: {title}
            Abstract: {abstract}

            Extract and Structure the following information:
            - **problem**: Problem/Research Question
            - **method**: Methodology/Approach
            - **results**: Key Findings
            - **limitations**: Limitations
            - **future_work**: Future Directions
            - **concepts**: List of 5-10 technical keywords (strings)

            Return strictly valid JSON.
            """

            try:
                # Use harded structured service
                summary_dict = generate_structured_json(prompt)
                
                # Reliability check & Retry
                if not REQUIRED_KEYS.issubset(summary_dict.keys()):
                    logger.warning(f"Summary for {pid} partial. Retrying once...")
                    try:
                        summary_dict = generate_structured_json(prompt)
                    except Exception:
                        pass # Keep original result if retry fails or ensure fallback below
                
                # Check again
                if not REQUIRED_KEYS.issubset(summary_dict.keys()):
                    summary_dict["_status"] = "partial_fallback"
                    summary_dict["_error"] = f"Missing keys: {REQUIRED_KEYS - summary_dict.keys()}"
                    # fill missing
                    for k in REQUIRED_KEYS:
                        if k not in summary_dict:
                            summary_dict[k] = "Not found (Extraction Failed)"
                else:
                    summary_dict["_status"] = "success"

                summaries[pid] = summary_dict
                
                # Update paper_concepts in state
                if "concepts" in summary_dict and isinstance(summary_dict["concepts"], list):
                    if "paper_concepts" not in state:
                        state["paper_concepts"] = {}
                    # Normalize concepts here too to match Graph Service
                    norm_concepts = [c.strip().lower() for c in summary_dict["concepts"] if isinstance(c, str)]
                    state["paper_concepts"][pid] = norm_concepts

                logger.info(f"Summarized {pid} (Status: {summary_dict['_status']})")

            except Exception as e:
                logger.warning(f"Failed summarizing {pid}: {e}")
                # Add reliable fallback
                summaries[pid] = {
                    key: "Generation Failed" for key in REQUIRED_KEYS
                }
                summaries[pid]["_status"] = "error"
                summaries[pid]["_error"] = str(e)

        state["paper_structured_summaries"] = summaries
        return state

paper_summarization_agent = PaperSummarizationAgent()
