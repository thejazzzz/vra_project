#File: agents/hypothesis_generation_agent.py
import logging
import json
import re
from typing import Dict, List, Any
from services.llm_service import generate_response
from services.research_service import get_relevant_context


logger = logging.getLogger(__name__)

def extract_json_object(text: str) -> str:
    """Extract the first complete JSON object from text."""
    start = text.find('{')
    if start == -1:
        return None
    
    brace_count = 0
    for i, char in enumerate(text[start:], start):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                return text[start:i+1]
    return None

class HypothesisGenerationAgent:
    """
    Phase 4: Generates testable research hypotheses based on identified gaps and trends.
    """
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("🧪 Hypothesis Agent: Generating hypotheses...")
        
        query = state.get("query", "")
        gaps = state.get("research_gaps", [])
        trends = state.get("concept_trends", {})
        
        # Select top gaps to focus on (Confidence > 0.6)
        active_gaps = [g for g in gaps if g.get("confidence", 0) > 0.6][:3]
        
        # If no strong gaps, use general context
        if not active_gaps:
             context_str = "No specific structural gaps found. Focus on general emerging trends."
        else:
             gap_contexts = []
             for g in active_gaps:
                 concept = g.get('concept', 'Unknown concept')
                 desc = g.get('description', 'No description available')
                 
                 
                 
                 # Targeted Retrieval
                 import asyncio
                 import concurrent.futures
                 
                 retrieval_query = f"{concept} limitations challenges future work"
                 try:
                     evidence = asyncio.run(get_relevant_context(
                         retrieval_query, 
                         limit=3, 
                         max_tokens=600,
                         agent_name="hypothesis_agent"
                     ))
                 except RuntimeError:
                     # Fallback: Loop likely running. Offload to clean thread to avoid deadlock.
                     logger.warning("HypothesisAgent: Event loop running. Offloading async retrieval to new thread.")
                     try:
                         with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                             # Run asyncio.run in a separate thread which has no loop issues
                             future = executor.submit(
                                 asyncio.run, 
                                 get_relevant_context(
                                     retrieval_query, 
                                     limit=3, 
                                     max_tokens=600,
                                     agent_name="hypothesis_agent"
                                 )
                             )
                             evidence = future.result(timeout=30)
                     except Exception as e2:
                         logger.error(f"HypothesisAgent: Threaded fallback failed: {e2}")
                         evidence = ""
                 except Exception as e:
                     logger.error(f"HypothesisAgent: Async retrieval error: {e}")
                     evidence = ""
                 
                 # FIX 6: Clearly label missing evidence
                 if not evidence:
                     evidence = "No strong supporting literature found."
                 
                 block = f"- GAP: {desc}\n  EVIDENCE FROM LITERATURE:\n{evidence}"
                 gap_contexts.append(block)
                 
             context_str = "\n".join(gap_contexts)

        # Prepare prompt
        prompt = f"""
        You are a Senior Principal Researcher. Your goal is to formulate NOVEL, TESTABLE research hypotheses for the topic: '{query}'.
        
        Use the following constraints:
        1. Hypotheses must bridge identified Gaps or extend Emerging Trends.
        2. Must be specific (avoid vague statements).
        3. Must propose a mechanism or relationship.
        
        CONTEXT:
        {context_str}
        
        TRENDS:
        {json.dumps(trends, indent=2) if trends else "No trend data available."}
        
        OUTPUT FORMAT:
        Return a JSON OBJECT with a key "hypotheses" containing a list of 3 hypotheses.
        Each hypothesis must have:
        - "id": "HYP_01" (etc)
        - "statement": "If X is applied to Y, then Z..."
        - "novelty_score": (1-10)
        - "testability_score": (1-10)
        - "supporting_evidence": "Based on the gap in..."
        """
        
        try:
            response_text = generate_response(prompt, model="gpt-4o-mini", temperature=0.7)
            # Extract JSON
            json_str = extract_json_object(response_text)
            if json_str:
                data = json.loads(json_str)
                hypotheses = data.get("hypotheses", [])
            else:
                logger.error("Failed to parse Hypothesis JSON")
                hypotheses = []
                
        except Exception as e:
            logger.error(f"Hypothesis Generation failed: {e}")
            hypotheses = []
            
        state["hypotheses"] = hypotheses
        return state

hypothesis_generation_agent = HypothesisGenerationAgent()
