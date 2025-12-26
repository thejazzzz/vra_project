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

class ReviewerAgent:
    """
    Phase 4.1: Critical Reviewer.
    Critiques hypotheses and assigns scores.
    """
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("🧐 Reviewer Agent: Critiquing hypotheses...")
        
        hypotheses = state.get("hypotheses", [])
        if not hypotheses:
            logger.warning("No hypotheses to review.")
            state["reviews"] = []
            return state

        # Prepare context for LLM
        hyp_text = "\n".join([f"ID: {h['id']}\nStatement: {h['statement']}\nEvidence: {h.get('supporting_evidence', 'Not provided')}\n" for h in hypotheses]) 
        
        prompt = f"""
        You are a Critical Reviewer for a top-tier scientific journal.
        Evaluate the following Research Hypotheses:

        {hyp_text}

        For EACH hypothesis, provide:
        - Critique: Identify any logical flaws, lack of evidence, or over-generalization.
        - Suggestions: How to improve testability.
        - Final Score: 1-10 (1=Reject, 10=Seminal Work).

        OUTPUT FORMAT:
        Return a JSON OBJECT with a key "reviews" containing a list of objects.
        Each object must have:
        - "hypothesis_id": "HYP_01" (matching input)
        - "critique": "The hypothesis assumes..."
        - "suggestions": "Consider controlling for..."
        - "score": 8
        """
        
        try:
            response_text = generate_response(prompt, model="gpt-4o-mini", temperature=0.5)
            # Extract JSON
            json_str = extract_json_object(response_text)
            if json_str:
                data = json.loads(json_str)
                reviews = data.get("reviews", [])
            else:
                logger.error("Failed to parse Review JSON")
                reviews = []
                
        except Exception as e:
            logger.error(f"Review generation failed: {e}")
            reviews = []
            
        state["reviews"] = reviews
        return state

reviewer_agent = ReviewerAgent()
