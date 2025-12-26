# agents/paper_summarization_agent.py
import logging
from services.structured_llm import generate_structured_json

logger = logging.getLogger(__name__)

class PaperSummarizationAgent:
    name = "paper_summarization_agent"

    def _summarize_single_paper(self, paper: dict) -> tuple[str, dict, list]:
        """
        Helper to process a single paper. Returns (pid, summary_dict, concepts).
        """
        REQUIRED_KEYS = {
            "problem", "method", "results", 
            "limitations", "future_work", "concepts"
        }
        
        pid = paper.get("canonical_id")
        if not pid:
            return None, None, None

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
            summary_dict = generate_structured_json(prompt)
            
            # Reliability check & Retry
            if not REQUIRED_KEYS.issubset(summary_dict.keys()):
                logger.warning(f"Summary for {pid} partial. Retrying once...")
                try:
                    summary_dict = generate_structured_json(prompt)
                except Exception:
                    pass 
            
            if not REQUIRED_KEYS.issubset(summary_dict.keys()):
                summary_dict["_status"] = "partial_fallback"
                summary_dict["_error"] = f"Missing keys: {REQUIRED_KEYS - summary_dict.keys()}"
                for k in REQUIRED_KEYS:
                    if k not in summary_dict:
                        summary_dict[k] = "Not found (Extraction Failed)"
            else:
                summary_dict["_status"] = "success"

            # Concepts
            concepts = []
            if "concepts" in summary_dict and isinstance(summary_dict["concepts"], list):
                concepts = [c.strip().lower() for c in summary_dict["concepts"] if isinstance(c, str)]

            return pid, summary_dict, concepts

        except Exception as e:
            logger.warning(f"Failed summarizing {pid}: {e}")
            fallback = {key: "Generation Failed" for key in REQUIRED_KEYS}
            fallback["_status"] = "error"
            fallback["_error"] = str(e)
            return pid, fallback, []

    def run(self, state):
        import concurrent.futures
        
        logger.info("📄 Summarizing paper content (Reliable Mode - Parallel)...")
        papers = state.get("selected_papers", [])
        summaries = {}
        
        if "paper_concepts" not in state:
            state["paper_concepts"] = {}

        # Parallel Execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_paper = {executor.submit(self._summarize_single_paper, paper): paper for paper in papers}
            
            for future in concurrent.futures.as_completed(future_to_paper):
                pid, summary_dict, concepts = future.result()
                if pid:
                    summaries[pid] = summary_dict
                    if concepts:
                        state["paper_concepts"][pid] = concepts
                    logger.info(f"Summarized {pid} (Status: {summary_dict.get('_status')})")

        state["paper_structured_summaries"] = summaries
        return state

paper_summarization_agent = PaperSummarizationAgent()
