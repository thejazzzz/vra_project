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

    def generate_report(self, state: Dict[str, Any]) -> str:
        logger.info("ReportGenerator: Starting report generation (Scaling Mode)...")
        
        # 1. Metadata Header (Phase 4)
        header = self._build_header(state)
        report_parts: List[str] = [header]
        
        report_parts.append(f"# Research Report: {state.get('query', 'Untitled')}\n")
        
        # 2. Plan
        sections = SectionPlanner.plan_report(state)
        
        # 3. Execute Sections
        for section in sections:
            logger.info(f"ReportGenerator: Processing section '{section.section_id}'")
            
            # Special handling for deterministic appendix
            if section.template_key == "deterministic_appendix":
                try:
                    appendix_content = AppendixGenerator.generate_appendix(state)
                    report_parts.append(appendix_content)
                except Exception as e:
                    logger.error(f"Failed to generate appendix: {e}")
                    report_parts.append(f"## {section.title}\n*Appendix generation failed due to service error.*\n")
                continue

            try:
                # Build Content
                context = ContextBuilder.build_context(section.section_id, state)
                audience_log = context.get("audience", "unknown")
                logger.info(f"[REPORT] Section={section.section_id} Audience={audience_log}")
                template = PROMPT_TEMPLATES.get(section.template_key)
                
                if not template:
                    logger.warning(f"No template found for {section.section_id}")
                    continue
                    
                # Format Prompt
                prompt = template.format(**context)
                
                # Resolve Provider Scheme
                # User config or default to OpenRouter (or Local if requested)
                report_provider_env = os.getenv("REPORT_PROVIDER", "local").lower()
                provider = LLMProvider.OPENROUTER
                
                if report_provider_env == "local":
                    provider = LLMProvider.LOCAL
                elif report_provider_env == "openai":
                    provider = LLMProvider.OPENAI
                elif report_provider_env == "azure":
                    provider = LLMProvider.AZURE

                # Generate
                content = generate_response(
                    prompt=prompt,
                    system_prompt=SYSTEM_PROMPT,
                    temperature=0.3,
                    provider=provider 
                )
                
                # Validation (Phase 4)
                if not self._validate_content(content, state):
                    content = "*Content flagged by safety validation filters.*"

                # Assemble
                report_parts.append(f"## {section.title}\n{content}\n")
                
            except Exception as e:
                logger.error(f"Failed to generate section {section.section_id}: {e}")
                report_parts.append(f"## {section.title}\n*Section generation failed due to service error.*\n")
                
            time.sleep(0.5)

        # 4. Final Footer (Provenance Summary)
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
