#File: services/reporting/report_generator.py
import logging
import time
import datetime
import os
from typing import Dict, Any, List

from services.reporting.section_planner import SectionPlanner
from services.reporting.context_builder import ContextBuilder
from services.reporting.prompts import PROMPT_TEMPLATES, SYSTEM_PROMPT
from services.reporting.appendix_generator import AppendixGenerator
from services.llm_service import generate_response
from services.llm_factory import LLMProvider, LLMFactory

logger = logging.getLogger(__name__)

class ReportGenerator:
    """
    Orchestrates the generation of a full research report.
    Phases: Plan -> Context -> Generate -> Assemble.
    Phase 4: Scaling, Appendices, Metadata.
    """

    @staticmethod
    def generate_section_content(section_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates content for a single section using the interactive workflow.
        Returns: {
            "content": str,
            "prompt_version": str,
            "model_name": str
        }
        """
        if section_id == "appendix":
             # Deterministic special case
             try:
                 content = AppendixGenerator.generate_appendix(state)
                 return {
                     "content": content,
                     "prompt_version": "deterministic_v1",
                     "model_name": "rules_engine"
                 }
             except Exception as e:
                 logger.error(f"Appendix generation failed: {e}")
                 raise e

        # 1. Build Context
        context = ContextBuilder.build_context(section_id, state)
        
        # 2. Get Template (Optimized)
        template_key = None
        
        # A. Check Cached Plan
        if state.get("report_state"):
             sections = state["report_state"].get("sections", [])
             sec = next((s for s in sections if s["section_id"] == section_id), None)
             if sec: template_key = sec.get("template_key")
        
        # B. Lightweight Lookup
        if not template_key:
             template_key = SectionPlanner.get_template_key(state, section_id)
             
        # C. Full Re-plan Fallback (and cache if appropriate - strictly we rely on lookup now)
        if not template_key:
             # Last resort
             plan = SectionPlanner.plan_report(state)
             sec = next((s for s in plan if s.section_id == section_id), None)
             if sec: template_key = sec.template_key
        
        if not template_key:
             raise ValueError(f"Could not determine template for section {section_id}")

        template = PROMPT_TEMPLATES.get(template_key)
        if not template:
             raise ValueError(f"Template not found for key {template_key}")

        # 3. Format Prompt
        prompt = template.format(**context)
        
        # 4. Resolve Provider and Model
        report_provider_env = os.getenv("REPORT_PROVIDER", "").lower()
        
        provider = None
        
        # Explicit Resolution
        if report_provider_env == "local":
            provider = LLMProvider.LOCAL
        elif report_provider_env == "openai":
            provider = LLMProvider.OPENAI
        elif report_provider_env == "azure":
            provider = LLMProvider.AZURE
        else:
            # Default to OPENROUTER for "openrouter", empty, unset, or unknown values
            provider = LLMProvider.OPENROUTER

        model_name = LLMFactory.get_default_model(provider)

        # 5. Generate
        logger.info(f"Generating section {section_id} with {provider} ({model_name})...")
        content = generate_response(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3, # Low temp for factual reporting
            provider=provider 
        )
        
        # 6. Basic Validation
        if "<html>" in content:
             logger.warning("Generated content contains HTML. Sanitizing...")
             content = content.replace("<html>", "").replace("</html>", "") # Basic strip
        
        return {
            "content": content,
            "prompt_version": getattr(template, "version", "v1.0"), 
            "model_name": model_name
        }

    async def generate_report_async(self, state: Dict[str, Any]) -> str:
        """
        Phase 12: Parallel Section Generation using asyncio.
        Orchestrates Phases 1-5 concurrently without blocking.
        """
        import asyncio
        from services.reporting.outline_generator import OutlineGenerator
        from services.reporting.anchor_generator import AnchorGenerator
        from services.reporting.independent_generator import IndependentGenerator
        from services.reporting.global_polisher import GlobalPolisher
        from services.reporting.section_cache import SectionCache
        
        import uuid
        session_id = state.get("session_id", uuid.uuid4().hex)
        state["session_id"] = session_id
        topic = state.get("query", "Unknown Topic")
        
        logger.info("ReportGenerator: Starting Phased Report Architecture...")
        
        # Phase 1: Outline
        outline_data = SectionCache.get(session_id, "outline")
        if not outline_data:
            logger.info("ReportGenerator: Running Phase 1 (Outline)...")
            outline = await asyncio.to_thread(OutlineGenerator.generate_outline, state)
            SectionCache.set(session_id, "outline", outline)
        else:
            logger.info("ReportGenerator: Found cached Outline.")
            outline = outline_data
            
        # Define the per-section execution pipeline
        semaphore = asyncio.Semaphore(3)
        
        from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
        
        @retry(
            wait=wait_exponential(min=2, max=10),
            stop=stop_after_attempt(3),
            retry=retry_if_exception_type((asyncio.TimeoutError, ConnectionError, OSError))
        )
        async def process_section(sec_dict: Dict[str, Any]) -> str:
            async with semaphore:
                return await asyncio.wait_for(_process_section_impl(sec_dict), timeout=120.0)

        async def _process_section_impl(sec_dict: Dict[str, Any]) -> str:
            sec_id = sec_dict.get("section_id", "unknown_section")
            sec_title = sec_dict.get("title", "Untitled Section")
            sec_desc = sec_dict.get("description", "")
            tw = sec_dict.get("target_words", 500)
            
            if not sec_dict.get("section_id"):
                 logger.warning("ReportGenerator received a section without 'section_id'. Falling back to 'unknown_section'.")
            
            # Check full section cache
            cached_section = SectionCache.get(session_id, f"finished_{sec_id}")
            if cached_section:
                 return f"## {sec_title}\n{cached_section['content']}\n"
                 
            # Phase 2: Anchors
            cached_anchors = SectionCache.get(session_id, f"anchors_{sec_id}")
            if not cached_anchors:
                anchors = await asyncio.to_thread(AnchorGenerator.generate_anchors, sec_title, sec_desc, state)
                SectionCache.set(session_id, f"anchors_{sec_id}", {"anchors": anchors})
            else:
                anchors = cached_anchors["anchors"]
                
            # Phase 3: Content Generation
            cached_content = SectionCache.get(session_id, f"content_{sec_id}")
            if not cached_content:
                content = await asyncio.to_thread(IndependentGenerator.generate_section, topic, sec_title, sec_desc, anchors, tw)
                SectionCache.set(session_id, f"content_{sec_id}", {"content": content})
            else:
                content = cached_content["content"]
                
            # Phase 4: Expansion
            final_section = await asyncio.to_thread(IndependentGenerator.expand_section_if_needed, content, tw)
            
            # Cache completed
            SectionCache.set(session_id, f"finished_{sec_id}", {"content": final_section})
            return f"## {sec_title}\n{final_section}\n"

        # Phase 12: Parallel Execution
        logger.info("ReportGenerator: Running Phase 12 (Parallel Processing)...")
        tasks = [process_section(sec) for sec in outline]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Assemble
        successful_results = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f"ReportGenerator: Section generation failed for {outline[i]['section_id']}: {res}")
                successful_results.append(f"## {outline[i]['title']}\n[Content generation failed: {res}]\n")
            else:
                successful_results.append(res)
                
        assembled_report = "\n\n".join(successful_results)
        
        # Phase 5: Global Consistency
        logger.info("ReportGenerator: Running Phase 5 (Global Polish)...")
        final_polished = await asyncio.to_thread(GlobalPolisher.run_consistency_pass, assembled_report)
        
        # Add Headers/Footers
        header = self._build_header(state)
        footer = self._build_footer(state)
        
        return f"{header}\n# Research Report: {topic}\n\n{final_polished}\n{footer}"
    
    def _build_header(self, state: Dict[str, Any]) -> str:
        """Generates reproducibility metadata block."""
        ag = state.get("author_graph", {})
        meta = ag.get("meta", {})
        
        # NOTE: Resolve model name dynamically
        provider_env = os.getenv("REPORT_PROVIDER", "local").lower()
        
        if provider_env == "local":
             provider = LLMProvider.LOCAL
        elif provider_env == "openai":
             provider = LLMProvider.OPENAI
        elif provider_env == "azure":
             provider = LLMProvider.AZURE
        else:
             provider = LLMProvider.OPENROUTER
             
        model_name = LLMFactory.get_default_model(provider)
        
        return f"""
---
Report Version: v1.6 (Local LLM Hybrid)
Generated At: {datetime.datetime.now(datetime.timezone.utc).isoformat()}
LLM Provider: {provider_env.upper()} ({model_name})
Metrics Valid: {meta.get("metrics_valid", "Unknown")}
Paper Count: {len(state.get("selected_papers", []))}
---
"""

    def _validate_content(self, content: str, state: Dict[str, Any]) -> bool:
        """Simple post-generation safety check."""
        # 1. Check for forbidden absolute terms
        forbidden = ["proven fact", "guaranteed truth", "indisputable"]
        for term in forbidden:
            if term in content.lower():
                logger.warning(f"Validation Violation: Found forbidden term '{term}'")
                return False
                
        # 2. Check for Hallucinated Titles (Heuristic: "Title:" pattern not in state)
        # This is expensive to check exhaustively, so we skip for now to save latency.
        # Ideally, we cross-reference citation keys.
        
        return True

    def _build_footer(self, state: Dict[str, Any]) -> str:
        papers = state.get("selected_papers", [])
        return f"""
---
**Note**: This report is generated by an AI agent using a specific subset of retrieved papers. 
Refer to the Evidence Appendix for full provenance.
"""
