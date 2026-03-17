# File: services/reporting/global_polisher.py
import os
import logging
from services.llm.orchestrator import LLMOrchestrator
from services.llm.token_manager import TokenManager

logger = logging.getLogger(__name__)

class GlobalPolisher:
    """
    Phase 5: Global Consistency Pass. Unifies tone and transitions across the full appended report.
    This is the ONLY step where the large context is used entirely.
    """
    @staticmethod
    def _load_prompt() -> str:
        prompt_path = os.path.join(os.path.dirname(__file__), '..', '..', 'prompts', 'consistency.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    async def run_consistency_pass(report_text: str) -> str:
        tm = TokenManager()
        # Ensure we don't blow up the final context natively. 
        original_tokens = tm.count_tokens(report_text)
        truncated_report = tm.truncate_to_limit(report_text, max_tokens=60000)
        truncated_tokens = tm.count_tokens(truncated_report)
        
        if truncated_tokens < original_tokens:
             logger.warning(f"GlobalPolisher: report truncated for final consistency pass (original_tokens={original_tokens}, truncated_tokens={truncated_tokens}, max_tokens=60000).")
        
        template = GlobalPolisher._load_prompt()
        prompt = template.format(report_text=truncated_report)
        
        logger.info("GlobalPolisher: Running final consistency pass across entire report...")
        final_content = await LLMOrchestrator.robust_generate_response(
            prompt=prompt,
            system_prompt="You are a meticulous final editor.",
            temperature=0.2
        )
        return final_content
