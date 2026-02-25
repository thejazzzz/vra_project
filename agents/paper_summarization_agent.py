# agents/paper_summarization_agent.py
import logging
from services.structured_llm import generate_structured_json
from database.db import SessionLocal
from database.models.paper_model import Paper

logger = logging.getLogger(__name__)

class PaperSummarizationAgent:
    name = "paper_summarization_agent"

    def _summarize_single_paper(self, paper: dict) -> tuple[str, dict, list, list]:
        """
        Helper to process a single paper. Returns (pid, summary_dict, concepts, relations).
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
        
        # Pull raw_text or fallback to abstract dynamically from DB
        content_to_analyze = f"Abstract: {abstract}"
        try:
            with SessionLocal() as db:
                db_paper = db.query(Paper).filter(Paper.canonical_id == pid).first()
                if db_paper and db_paper.raw_text:
                    content_to_analyze = f"Full Text Extract:\n{db_paper.raw_text[:12000]}"
                elif db_paper and db_paper.abstract:
                    content_to_analyze = f"Abstract:\n{db_paper.abstract}"
        except Exception as e:
            logger.warning(f"Could not load raw_text for {pid}: {e}")
        
        prompt = f"""
        Analyze the following research paper based on its title and text contents.
        
        Paper Title: {title}
        {content_to_analyze}

        Extract and Structure the following information:
        - **problem**: Problem/Research Question
        - **method**: Methodology/Approach
        - **results**: Key Findings
        - **limitations**: Limitations
        - **future_work**: Future Directions
        - **concepts**: List of 5-10 technical keywords (strings)
        - **relations**: List of relationships between concepts found in this paper. Each relation must be an object with "source" (string, a concept), "target" (string, a concept), and "relation" (string, e.g., "uses", "extends", "improves", "related_to"). Maximum 15 relations per paper.

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
                missing = list(REQUIRED_KEYS - summary_dict.keys())
                summary_dict["_error"] = f"Missing keys: {missing}"
                for k in REQUIRED_KEYS:
                    if k not in summary_dict:
                        summary_dict[k] = "Not found (Extraction Failed)"
            else:
                summary_dict["_status"] = "success"

            # Concepts
            concepts = []
            if "concepts" in summary_dict and isinstance(summary_dict["concepts"], list):
                concepts = [c.strip().lower() for c in summary_dict["concepts"] if isinstance(c, str)]

            # Relations
            relations = []
            if "relations" in summary_dict and isinstance(summary_dict["relations"], list):
                for r in summary_dict["relations"]:
                    if isinstance(r, dict) and "source" in r and "target" in r and "relation" in r:
                        r["source"] = str(r["source"]).strip().lower()
                        r["target"] = str(r["target"]).strip().lower()
                        relations.append({
                            "source": r["source"],
                            "target": r["target"],
                            "relation": r["relation"],
                            "evidence": {"paper_id": pid, "excerpt": "Extracted by summarization agent"}
                        })

            return pid, summary_dict, concepts, relations

        except Exception as e:
            logger.warning(f"Failed summarizing {pid}: {e}")
            fallback = {key: "Generation Failed" for key in REQUIRED_KEYS}
            fallback["_status"] = "error"
            fallback["_error"] = str(e)
            return pid, fallback, [], []

    def run(self, state):
        import concurrent.futures
        
        logger.info("📄 Summarizing paper content (Reliable Mode - Parallel)...")
        papers = state.get("selected_papers", [])
        summaries = {}
        
        if "paper_relations" not in state:
            state["paper_relations"] = {}
        if "paper_concepts" not in state:
            state["paper_concepts"] = {}

        # Parallel Execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_paper = {executor.submit(self._summarize_single_paper, paper): paper for paper in papers}
            
            for future in concurrent.futures.as_completed(future_to_paper):
                pid, summary_dict, concepts, relations = future.result()
                if pid:
                    summaries[pid] = summary_dict
                    if concepts:
                        state["paper_concepts"][pid] = concepts
                    if relations:
                        state["paper_relations"][pid] = relations
                    logger.info(f"Summarized {pid} (Status: {summary_dict.get('_status')})")

        state["paper_structured_summaries"] = summaries
        return state

paper_summarization_agent = PaperSummarizationAgent()
