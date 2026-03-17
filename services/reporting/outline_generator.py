# File: services/reporting/outline_generator.py
import os
import logging
import re
from typing import Dict, Any, List

from services.llm.orchestrator import LLMOrchestrator

logger = logging.getLogger(__name__)

class OutlineGenerator:
    """
    Phase 1: Outline Engine. Generates a blueprint for the report to prevent repetition and hallucination.
    """
    @staticmethod
    def _load_prompt() -> str:
        prompt_path = os.path.join(os.path.dirname(__file__), '..', '..', 'prompts', 'outline.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    async def generate_outline(state: Dict[str, Any]) -> List[Dict[str, Any]]:
        template = OutlineGenerator._load_prompt()
        prompt = template.format(
            topic=state.get("query", "Unknown Topic"),
            report_type=state.get("report_type", "Comprehensive Academic Report"),
            target_word_count=state.get("target_length_words", 5000),
            audience=state.get("audience", "Academic Peers")
        )
        
        logger.info("OutlineGenerator: Generating structured report outline...")
        outline_content = await LLMOrchestrator.robust_generate_response(
            prompt=prompt, 
            system_prompt="You are an expert academic report outliner. Follow the instructions strictly.", 
            temperature=0.2
        )
        
        return OutlineGenerator._parse_outline(outline_content)

    @staticmethod
    def _parse_outline(text: str) -> List[Dict[str, Any]]:
        sections = []
        # split by numbered list (e.g. "1. Introduction")
        blocks = re.split(r'\n(?=\d+\.)', "\n" + text.strip())
        
        section_idx = 0
        for block in blocks:
            if not block.strip():
                continue
            lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
            if not lines: continue
            
            title_line = lines[0]
            title = re.sub(r'^\d+\.\s*', '', title_line)
            
            description = ""
            target_words = 500
            
            for line in lines[1:]:
                if line.lower().startswith("description:"):
                    description = line.split(":", 1)[1].strip()
                elif line.lower().startswith("target word count:"):
                    tw_str = line.split(":", 1)[1].strip()
                    tw_match = re.search(r'\d+', tw_str)
                    if tw_match:
                        target_words = int(tw_match.group())
                        
            sections.append({
                "section_id": f"section_{section_idx}",
                "title": title,
                "description": description,
                "target_words": target_words,
                "status": "pending",
                "section_type": "standard",
                "content": ""
            })
            section_idx += 1
            
        return sections
