# File: services/reporting/independent_generator.py
import os
import logging

from services.llm.orchestrator import LLMOrchestrator

logger = logging.getLogger(__name__)

class IndependentGenerator:
    """
    Phase 3 & 4: Independent Section Generation & Smart Expansion.
    Generates sections independently using specific anchors to save tokens.
    """
    @staticmethod
    def _load_prompt(filename: str) -> str:
        prompt_path = os.path.join(os.path.dirname(__file__), '..', '..', 'prompts', filename)
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def _escape_braces(text: str) -> str:
        if not isinstance(text, str):
            return str(text)
        return text.replace("{", "{{").replace("}", "}}")

    @staticmethod
    async def generate_section(topic: str, section_title: str, section_description: str, anchors: str, target_words: int, writing_style: str = "Formal academic") -> str:
        template = IndependentGenerator._load_prompt('section.txt')
        prompt = template.format(
            topic=IndependentGenerator._escape_braces(topic),
            section_title=IndependentGenerator._escape_braces(section_title),
            section_description=IndependentGenerator._escape_braces(section_description),
            anchors=IndependentGenerator._escape_braces(anchors),
            target_words=target_words,
            writing_style=IndependentGenerator._escape_braces(writing_style)
        )
        
        logger.info(f"IndependentGenerator: Generating section '{section_title}' ({target_words} words)...")
        content = await LLMOrchestrator.robust_generate_response(
            prompt=prompt,
            system_prompt="You are an expert academic writer.",
            temperature=0.3
        )
        return content

    @staticmethod
    async def expand_section_if_needed(section_text: str, target_words: int) -> str:
        """Phase 4: Only expands if the section heavily missed its word budget."""
        current_words = len(section_text.split())
        if current_words >= target_words * 0.9: # Allow 10% tolerance
            return section_text
            
        words_to_add = target_words - current_words
        if words_to_add < 100:
            return section_text
            
        logger.info(f"IndependentGenerator: Smart Expand - '{current_words}' -> '{target_words}' words...")
        template = IndependentGenerator._load_prompt('expansion.txt')
        prompt = template.format(
            section_text=IndependentGenerator._escape_braces(section_text),
            words_to_add=words_to_add
        )
        
        expanded_content = ""
        try:
            expanded_content = await LLMOrchestrator.robust_generate_response(
                prompt=prompt,
                system_prompt="You are an expert academic writer expanding a report.",
                temperature=0.4
            )
        except Exception as e:
            logger.warning(f"IndependentGenerator: Smart Expand failed: {e}. Falling back to original text.")
            return section_text
            
        if not expanded_content or len(expanded_content.strip()) < len(section_text) * 0.5:
            logger.warning("IndependentGenerator: Smart Expand returned invalid or excessively short content. Falling back to original text.")
            return section_text
            
        return expanded_content
