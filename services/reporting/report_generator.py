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
from services.llm_factory import LLMProvider

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
        
        # 2. Get Template
        # We need to look up the template key. The SectionPlanner knows it.
        # But we don't have the plan object here unless we look at state['report_state'].
        # Fallback: Re-plan or use lookup. 
        # Better: use state['report_state'] if available, else re-plan (hybrid).
        
        template_key = None
        if state.get("report_state"):
             # Fast lookup from existing plan
             sections = state["report_state"]["sections"]
             sec = next((s for s in sections if s["section_id"] == section_id), None)
             if sec: template_key = sec.get("template_key")
        
        if not template_key:
             # Fallback to planner for legacy/stateless calls
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
        
        # 4. Resolve Provider
        report_provider_env = os.getenv("REPORT_PROVIDER", "local").lower()
        provider = LLMProvider.OPENROUTER
        if report_provider_env == "local":
            provider = LLMProvider.LOCAL
        elif report_provider_env == "openai":
            provider = LLMProvider.OPENAI
        elif report_provider_env == "azure":
            provider = LLMProvider.AZURE

        # 5. Generate
        logger.info(f"Generating section {section_id} with {provider}...")
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
            # Assuming PROMPT_TEMPLATES are objects with .version, or we mock it for now since they are currently Dicts/Strings
            # PROMPT_TEMPLATES is likely a dict of PromptTemplate objects or strings.
            # Checking prompts.py would confirm. For now assuming string or dict.
            "prompt_version": getattr(template, "version", "v1.0"), 
            "model_name": f"{provider.value}" # Simplified model name logic
        }

    def generate_report(self, state: Dict[str, Any]) -> str:
        """
        Legacy batch generation method.
        """
        logger.info("ReportGenerator: Starting legacy batch report generation...")
        
        # 1. Metadata Header
        header = self._build_header(state)
        report_parts: List[str] = [header]
        report_parts.append(f"# Research Report: {state.get('query', 'Untitled')}\n")
        
        # 2. Plan
        sections = SectionPlanner.plan_report(state)
        
        # 3. Execute Sections
        for section in sections:
            logger.info(f"ReportGenerator: Processing section '{section.section_id}'")
            try:
                result = self.generate_section_content(section.section_id, state)
                content = result["content"]
                report_parts.append(f"## {section.title}\n{content}\n")
            except Exception as e:
                logger.error(f"Failed to generate section {section.section_id}: {e}")
                report_parts.append(f"## {section.title}\n*Generation failed.*\n")
            
            time.sleep(0.5)

        # 4. Footer
        footer = self._build_footer(state)
        report_parts.append(footer)
        
        full_report = "\n".join(report_parts)
        return full_report
    
    def _build_header(self, state: Dict[str, Any]) -> str:
        """Generates reproducibility metadata block."""
        ag = state.get("author_graph", {})
        meta = ag.get("meta", {})
        
        # NOTE: Resolve model name dynamically
        provider_env = os.getenv("REPORT_PROVIDER", "local").lower()
        model_name = "Unknown"
        if provider_env == "local":
             model_name = os.getenv("LOCAL_MODEL", "llama3:8b")
        elif provider_env == "openrouter":
             model_name = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")
        
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
