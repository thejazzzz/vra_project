import logging
import json
import re
from typing import Dict, List, Any
from services.llm_service import generate_response


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
            context_str = "\n".join([f"- Gap in '{g.get('concept')}': {g.get('description')}" for g in active_gaps])
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
