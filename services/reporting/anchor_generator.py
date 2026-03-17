# File: services/reporting/anchor_generator.py
import os
import logging
from typing import Dict, Any

from services.llm.orchestrator import LLMOrchestrator
from services.llm.token_manager import TokenManager

logger = logging.getLogger(__name__)

class AnchorGenerator:
    """
    Phase 2: Research Anchor Generator. Extracts key bullet points from paper context specific to a section.
    """
    @staticmethod
    def _load_prompt() -> str:
        prompt_path = os.path.join(os.path.dirname(__file__), '..', '..', 'prompts', 'anchors.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def _escape_braces(text: str) -> str:
        if not isinstance(text, str):
            return str(text)
        return text.replace("{", "{{").replace("}", "}}")

    @staticmethod
    async def generate_anchors(section_title: str, section_description: str, state: Dict[str, Any]) -> str:
        template = AnchorGenerator._load_prompt()
        
        # Build context from papers
        papers = state.get("selected_papers", [])
        summaries = state.get("paper_summaries", {})
        
        context_lines = []
        for p in papers:
            pid = p.get("paper_id")
            title = p.get("title", "")
            summary = summaries.get(pid, p.get("abstract", ""))
            context_lines.append(f"Title: {title}\nSummary-Abstract: {summary}")
            
        raw_context = "\n\n".join(context_lines)
        
        # Enforce token limit on context using the TokenManager
        tm = TokenManager()
        truncated_context = tm.truncate_to_limit(raw_context, max_tokens=15000)
        
        prompt = template.format(
            section_title=section_title,
            section_description=section_description,
            context=truncated_context
        )
        
        logger.info(f"AnchorGenerator: Generating semantic anchors for '{section_title}'...")
        anchors_content = await LLMOrchestrator.robust_generate_response(
            prompt=prompt,
            system_prompt="You are an expert research analyst. Follow instructions strictly.",
            temperature=0.2
        )
        return anchors_content
