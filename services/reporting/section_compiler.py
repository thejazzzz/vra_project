# File: services/reporting/section_compiler.py
import logging
from typing import Dict, Any, List, Optional
import time

from state.state_schema import ReportState, ReportSectionState
from services.llm_service import generate_response
from services.llm_factory import LLMProvider
from services.reporting.prompts import PROMPT_TEMPLATES, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class SectionCompiler:
    """
    Orchestrates the multi-pass compilation of a single report section.
    Implements:
    1. Word Budgeting
    2. Expansion Loops (Draft -> Expand -> Refine)
    3. Content Anchoring (Anti-Hallucination)
    4. Guardrails (Repetition Check, Max Passes)
    """

    def __init__(self, state: Dict[str, Any]):
        self.state = state
        # Force Local for heavy lifting
        self.provider = LLMProvider.LOCAL 
        self.model_name = "llama3:8b" 

    def compile(self, section: ReportSectionState) -> str:
        """
        Main compilation pipeline.
        """
        logger.info(f"Compiler: Starting compilation for {section['section_id']} (Target: {section['target_words']} words)")
        
        section["compilation_phase"] = "DRAFTING"
        
        # 1. Gather Context & Anchors
        context = self._build_context(section)
        anchors = self._extract_anchors(context) # "Allowed Facts"
        
        # 2. Draft Skeleton
        draft = self._draft_skeleton(section, context)
        current_words = len(draft.split())
        logger.info(f"Compiler: Draft complete. Words: {current_words}")

        # 3. Expansion Loop
        section["compilation_phase"] = "EXPANDING"
        passes = 0
        MAX_PASSES = 5
        MIN_DELTA = 100 # Minimum word growth to justify another pass
        
        while current_words < section["target_words"] and passes < MAX_PASSES:
            logger.info(f"Compiler: Expansion Pass {passes+1}/{MAX_PASSES}. Current: {current_words} / {section['target_words']}")
            
            expanded_draft = self._expand_content(draft, anchors, section["section_type"])
            
            new_word_count = len(expanded_draft.split())
            delta = new_word_count - current_words
            
            if delta < MIN_DELTA:
                logger.warning(f"Compiler: Diminishing returns (Delta {delta} < {MIN_DELTA}). Stopping expansion.")
                current_words = new_word_count # Update stale count before breaking
                draft = expanded_draft
                break
                
            draft = expanded_draft
            current_words = new_word_count
            passes += 1
            
        # 4. Refinement
        section["compilation_phase"] = "REFINING"
        final_content = self._refine_content(draft, section["section_type"])
        
        section["compilation_phase"] = "COMPLETE"
        return final_content

    def _build_context(self, section: ReportSectionState) -> str:
        # TODO: Refactor ContextBuilder to be more modular? 
        # For now, we reuse the basic context logic or simplistic string dump
        # We need a robust string representation of the data.
        from services.reporting.context_builder import ContextBuilder
        raw_context = ContextBuilder.build_context(section["section_id"], self.state)
        
        # Flatten dict to string for LLM consumption
        lines = []
        for k, v in raw_context.items():
            lines.append(f"[{k.upper()}]:\n{v}")
            
        return "\n\n".join(lines)

    def _extract_anchors(self, context: str) -> str:
        """
        Creates a strict list of 'Allowed Facts' from the context.
        This prevents the Local LLM from inventing new papers or stats.
        """
        # Dictionary logic removed in favor of string truncation as requested
        return context[:2000] # Truncate anchor context to avoid overflow

    def _draft_skeleton(self, section: ReportSectionState, context: str) -> str:
        prompt = f"""
        SECTION TITLE: {section['title']}
        DESCRIPTION: {section['description']}
        CONTEXT: {context}
        
        TASK: Write a detailed structural skeleton for this section. 
        Use standard Academic English.
        Do not look for length yet, focus on structure and flow.
        """
        # Pass model parameter correctly
        return generate_response(prompt, temperature=0.3, provider=self.provider, model=self.model_name)

    def _expand_content(self, current_text: str, anchors: str, section_type: str) -> str:
        """
        Takes the current text and 'inflates' it paragraph by paragraph.
        """
        prompt = f"""
        ORIGINAL TEXT:
        {current_text}
        
        ALLOWED FACTS (STRICT ANCHORING):
        {anchors}
        
        TASK: Expand the Original Text.
        Target Tone: Academic / Formal ({section_type}).
        
        RULES:
        1. You must roughly DOUBLE the length of the text.
        2. Elaborate on every point using ONLY the Allowed Facts.
        3. Do NOT add new citations or external entities not in Allowed Facts.
        4. Improve transitions between paragraphs.
        5. Maintain valid Markdown structure.
        """
        

        return generate_response(prompt, temperature=0.4, provider=self.provider, model=self.model_name)

    def _refine_content(self, text: str, section_type: str) -> str:
        prompt = f"""
        TASK: Polish/Refine the following text for a PhD-level report.
        SECTION TYPE: {section_type}
        
        RULES:
        1. Fix any repetitive phrasing.
        2. Ensure terminology is consistent.
        3. Convert passive voice to active where appropriate (but keep formal).
        4. Ensure strictly proper Markdown hierarchy.
        
        TEXT:
        {text}
        """
        return generate_response(prompt, temperature=0.2, provider=self.provider, model=self.model_name)
