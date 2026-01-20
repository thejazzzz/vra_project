# File: services/reporting/section_compiler.py
import logging
from typing import Dict, Any, List, Optional
import time

from state.state_schema import ReportState, ReportSectionState
from services.llm_service import generate_response
from services.llm_factory import LLMProvider
from services.reporting.prompts import PROMPT_TEMPLATES, SYSTEM_PROMPTS
from enum import Enum
import os

class CostLimitExceededError(Exception):
    """Raised when cloud call limit is reached."""
    pass

class CompilationPhase(Enum):
    DRAFT = "DRAFTING"
    EXPAND = "EXPANDING"
    REFINE = "REFINING"
    ABSTRACT = "ABSTRACT"

logger = logging.getLogger(__name__)

class SectionCompiler:
    """
    Orchestrates the multi-pass compilation of a single report section.
    Implements:
    1. Word Budgeting
    2. Expansion Loops (Draft -> Expand -> Refine)
    3. Content Anchoring (Anti-Hallucination)
    4. Guardrails (Repetition Check, Max Passes)
    5. Late Abstract Synthesis
    """

    def __init__(self, state: Dict[str, Any]):
        self.state = state
        
        # --- Hybrid Configuration ---
        self.hybrid_mode = os.getenv("VRA_HYBRID_MODE", "false").lower() == "true"
        
        # Primary (High Quality)
        self.primary_provider = self._parse_provider(os.getenv("PRIMARY_PROVIDER") or os.getenv("REPORT_PROVIDER") or "openai")
        self.primary_model = os.getenv("PRIMARY_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o"
        
        # Secondary (High Speed/Low Cost)
        self.secondary_provider = self._parse_provider(os.getenv("SECONDARY_PROVIDER") or "local")
        self.secondary_model = os.getenv("SECONDARY_MODEL") or os.getenv("LOCAL_MODEL") or "llama3:8b"
        
        # Safety
        self.max_cloud_calls = int(os.getenv("MAX_CLOUD_CALLS", "15"))
        
        # Default State (Will be overridden by _resolve_provider)
        self.provider = self.primary_provider
        self.model_name = self.primary_model
        
    def _parse_provider(self, name: str) -> LLMProvider:
        name = name.lower()
        if name == "openai": return LLMProvider.OPENAI
        if name == "azure": return LLMProvider.AZURE
        if name == "openrouter": return LLMProvider.OPENROUTER
        return LLMProvider.LOCAL

    def _resolve_provider(self, phase: CompilationPhase, section_type: str = "") -> tuple[LLMProvider, str]:
        """
        Determines the best (Provider, Model) based on Phase, Logic, and Config.
        """
        # Rule 1: Abstract ALWAYS uses Primary (High Reasoning)
        if phase == CompilationPhase.ABSTRACT:
            return self.primary_provider, self.primary_model
            
        # Rule 2: If Hybrid is OFF, use Primary/Default for everything
        if not self.hybrid_mode:
            # Fallback to legacy behavior (Primary is set to REPORT_PROVIDER)
            return self.primary_provider, self.primary_model
            
        # Rule 3: Hybrid Logic
        if phase == CompilationPhase.REFINE:
            return self.primary_provider, self.primary_model # High Polish
            
        if phase == CompilationPhase.EXPAND:
            return self.secondary_provider, self.secondary_model # Bulk Volume
            
        if phase == CompilationPhase.DRAFT:
            # Complex sections need reasoning
            if section_type in ["INTRO", "CONCLUSION", "ANALYSIS", "LITERATURE"]:
                 return self.primary_provider, self.primary_model
            else:
                 return self.secondary_provider, self.secondary_model # Method/Impl are structural
                 
        return self.primary_provider, self.primary_model

    def _check_cost_guardrail(self, provider: LLMProvider):
        """
        Circuit breaker for cloud costs.
        """
        if provider != LLMProvider.LOCAL:
            current_calls = self.state.get("metrics", {}).get("cloud_calls", 0)
            if current_calls >= self.max_cloud_calls:
                 logger.warning(f"Cost Guardrail: Max cloud calls ({self.max_cloud_calls}) exceeded.")
                 raise CostLimitExceededError("Max cloud calls reached.")
            
            # Increment
            if "metrics" not in self.state: self.state["metrics"] = {}
            self.state["metrics"]["cloud_calls"] = current_calls + 1
            
    def _resolve_safe_provider(self, phase: CompilationPhase, section_type: str = "") -> tuple[LLMProvider, str]:
        """
        Resolves provider with fallback logic for cost/errors.
        """
        provider, model = self._resolve_provider(phase, section_type)
        
        try:
            self._check_cost_guardrail(provider)
            return provider, model
        except CostLimitExceededError:
            # Fallback to Secondary
            fallback_provider = self.secondary_provider
            fallback_model = self.secondary_model
            
            # Verify fallback isn't also costly (unless it's local, which is safe)
            # If secondary is also paid, we might need a recursive check or hard stop.
            # For now, we assume Secondary = Local or Cheap. 
            # If Secondary != Local, we should check cost guardrail again? 
            # If Max Cloud calls reached, we shouldn't use ANY cloud provider.
            
            if fallback_provider != LLMProvider.LOCAL:
                 # Re-check guardrail. If we are already over limit, report must stop.
                 try:
                     self._check_cost_guardrail(fallback_provider)
                 except CostLimitExceededError as e:
                     raise CostLimitExceededError(
                         f"Cost Limit Exceeded even with Fallback Provider ({fallback_provider}). Stopping report."
                     ) from e

            logger.warning(f"[Hybrid] Event=FALLBACK | Reason=COST_LIMIT | Phase={phase.value} | To={fallback_provider} ({fallback_model})")
            
            # Indicate in state
            if "warnings" not in self.state: self.state["warnings"] = []
            self.state["warnings"].append(f"Hybrid Fallback triggered for {phase.value} -> {fallback_model}")
            
            return fallback_provider, fallback_model 

    def compile(self, section: ReportSectionState) -> str:
        """
        Main compilation pipeline.
        """
        logger.info(f"Compiler: Starting compilation for {section['section_id']} (Target: {section['target_words']} words)")
        
        # Special Path for Abstract
        if section["section_id"] == "abstract":
            return self._compile_abstract(section)

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
            
            expanded_draft = self._expand_content(draft, anchors, section["section_type"], section["target_words"])
            
            # Repetition Check
            if self._repetition_score(draft, expanded_draft) > 0.8:
                logger.warning("Compiler: High repetition detected. Stopping expansion.")
                break

            new_word_count = len(expanded_draft.split())
            delta = new_word_count - current_words
            
            if delta < MIN_DELTA and passes > 0: # Allow first pass even if small
                logger.warning(f"Compiler: Diminishing returns (Delta {delta} < {MIN_DELTA}). Stopping expansion.")
                draft = expanded_draft # Accept small gain
                current_words = new_word_count 
                break
                
            draft = expanded_draft
            current_words = new_word_count
            passes += 1
            
        # 4. Refinement
        section["compilation_phase"] = "REFINING"
        final_content = self._refine_content(draft, section["section_type"])
        
        # 5. Sanitization
        final_content = self._sanitize(final_content)

        section["compilation_phase"] = "COMPLETE"
        return final_content

    def _build_context(self, section: ReportSectionState) -> str:
        from services.reporting.context_builder import ContextBuilder
        raw_context = ContextBuilder.build_context(section["section_id"], self.state)
        
        lines = []
        for k, v in raw_context.items():
            lines.append(f"[{k.upper()}]:\n{v}")
            
        return "\n\n".join(lines)

    def _extract_anchors(self, context: str) -> str:
        """
        Robustly extracts 'bullet-safe' anchors to avoid partial sentences.
        """
        lines = context.splitlines()
        anchors = []
        total_len = 0
        MAX_LEN = 1500
        
        for line in lines:
            line = line.strip()
            # Keep non-empty lines that aren't excessively long (likely garbage/base64)
            if line and len(line) < 200:
                anchors.append(line)
                total_len += len(line)
            
            if total_len > MAX_LEN:
                break
                
        return "\n".join(anchors)

    def _generate_with_fallback(self, prompt: str, system_prompt: str, phase: CompilationPhase, section_type: str = "", temperature: float = 0.3) -> str:
        """
        Robust generation wrapper:
        1. Resolves provider safely (checking cost limits).
        2. Tries generation.
        3. On Primary Provider error, falls back to Secondary.
        """
        # 1. Resolve Provider (Handles Cost Limit Fallback internally)
        provider, model_name = self._resolve_safe_provider(phase, section_type)
        
        try:
             # 2. Attempt Generation
             content = generate_response(
                prompt,
                temperature=temperature,
                provider=provider,
                model=model_name,
                system_prompt=system_prompt
             )
             logger.info(f"[Hybrid] Phase={phase.value} | Provider={provider} | Model={model_name} | Status=SUCCESS")
             return content
             
        except Exception as e:
             # 3. Handle Provider Errors (Timeout, 500, etc)
             is_primary = (provider == self.primary_provider) and (self.primary_provider != self.secondary_provider)
             
             if is_primary:
                  logger.warning(f"[Hybrid] Event=FALLBACK | Reason=PROVIDER_ERROR | From={provider} | Error={str(e)}")
                  
                  # Switch to Secondary
                  fallback_provider = self.secondary_provider
                  fallback_model = self.secondary_model
                  
                  # Cost Check for Fallback? (Usually safe, but good to be sure if Secondary is not Local)
                  # _resolve_safe_provider logic usually covers cost, but here we are runtime switching.
                  # If Secondary is Local, it's free. If it's paid, we might hit limits, but we are in emergency fallback.
                  # Let's assume Secondary is safe-ish or we accept the risk to finish the report.
                  
                  logger.info(f"[Hybrid] Retrying with Secondary: {fallback_provider} ({fallback_model})")
                  
                  # Enforce Cost Guardrail for Fallback Provider
                  # Even if it's "secondary", if it's not LOCAL, we must check limits.
                  if fallback_provider != LLMProvider.LOCAL:
                      self._check_cost_guardrail(fallback_provider)
                  
                  try:
                       content = generate_response(
                            prompt,
                            temperature=temperature,
                            provider=fallback_provider,
                            model=fallback_model,
                            system_prompt=system_prompt
                       )
                       
                       # Record Warning
                       if "warnings" not in self.state: self.state["warnings"] = []
                       self.state["warnings"].append(f"Fallback used for {phase.value} due to error: {str(e)}")
                       
                       return content
                  except Exception as e2:
                       logger.error(f"[Hybrid] Event=FALLBACK_FAILED | From={fallback_provider} | Error={str(e2)}")
                       raise e2 # Rethrow secondary error
             
             else:
                  # It was already Secondary or Local, just fail
                  raise e

    def _draft_skeleton(self, section: ReportSectionState, context: str) -> str:
        system_prompt = SYSTEM_PROMPTS.get("draft")
        
        # Safer generic fallback
        t_key = section.get("template_key", "draft_skeleton")
        template = PROMPT_TEMPLATES.get(t_key, PROMPT_TEMPLATES["draft_skeleton"])

        prompt = template.format(
            title=section['title'],
            description=section['description'],
            context=context,
            target_words=section['target_words']
        )
        
        return self._generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            phase=CompilationPhase.DRAFT,
            section_type=section['section_type'],
            temperature=0.3
        )

    def _expand_content(self, current_text: str, anchors: str, section_type: str, section_target_words: int) -> str:
        system_prompt = SYSTEM_PROMPTS.get("expand")
        
        current_words = len(current_text.split())
        
        # Safer expansion math: Aim to fill remaining budget, but don't over-inflate small drafts instantly
        remaining = section_target_words - current_words
        # Target = Current + (Remaining capped, or Min 200 growth)
        # This means: "Try to finish the section, or at least add 200 words."
        expansion_goal = min(remaining, max(200, current_words)) 
        target_words = current_words + expansion_goal

        prompt = PROMPT_TEMPLATES["expand_content"].format(
            content=current_text,
            anchors=anchors,
            target_words=target_words,
            section_type=section_type
        )
        
        return self._generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            phase=CompilationPhase.EXPAND,
            section_type=section_type,
            temperature=0.4
        )

    def _refine_content(self, text: str, section_type: str) -> str:
        system_prompt = SYSTEM_PROMPTS.get("refine")
        
        prompt = PROMPT_TEMPLATES["refine_content"].format(
            section_type=section_type,
            content=text
        )
        
        return self._generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            phase=CompilationPhase.REFINE,
            section_type=section_type,
            temperature=0.2
        )

    def _repetition_score(self, old: str, new: str) -> float:
        """
        Simple n-gram overlap check to detect if generic LLM loop is just rephrasing.
        """
        if not old or not new: return 0.0
        
        old_words = old.split()
        new_words = new.split()
        
        # Check first 500 words (intro reuse) or random sampling? 
        # User suggested first 500.
        limit = 500
        old_set = set(old_words[:limit])
        new_set = set(new_words[:limit])
        
        if not new_set: return 0.0
        
        return len(old_set & new_set) / len(new_set)

    def _sanitize(self, text: str, forbidden_phrases: Optional[List[str]] = None, line_length_threshold: int = 200) -> str:
        """
        Removes meta-commentary that might leak through logic.
        Now uses targeted replacement and skips long lines ("academic content").
        """
        import re # distinct import scope or file level? File level is better but I can't reach it here easily without MultiReplace. 
        # I will rely on Python allowing import inside function or use MultiReplace to add import and change function.
        # Let's use local import for safety if I don't want to touch top of file, or better, use MultiReplace.
        
        if forbidden_phrases is None:
             forbidden_phrases = ["in this section", "this paper", "we discuss", "aim of this chapter"]
        
        # Compile regex for case-insensitive replacement
        # \b word boundary might be good but phrases might contain spaces. 
        # Simple string replacement logic:
        pattern = re.compile("|".join(map(re.escape, forbidden_phrases)), re.IGNORECASE)
        
        lines = []
        for line in text.splitlines():
            # 1. Skip filtering for long lines (likely genuine content)
            if len(line) > line_length_threshold:
                lines.append(line)
                continue
                
            # 2. Targeted Replacement
            clean_line = pattern.sub("", line)
            
            # 3. Only omit if line is now empty/whitespace (was mostly meta)
            if clean_line.strip():
                lines.append(clean_line)
                
        return "\n".join(lines)

    # --- Abstract Specialization ---

    def _compile_abstract(self, section: ReportSectionState) -> str:
        """
        Compiles the Abstract using strict 'Synthesis of Reality' from completed chapters.
        """
        # Guard: Ensure all other dependencies are accepted
        incomplete = [
            s["section_id"] for s in self.state.get("sections", [])
            if s["section_id"] != "abstract" and s.get("status") != "accepted"
        ]
        if incomplete:
            raise ValueError(
                f"Cannot generate abstract. Unaccepted sections: {incomplete}"
            )

        section["status"] = "generating"


        # 1. Gather Inputs from Reality
        inputs = self._build_abstract_inputs()
        
        # 2. Synthesize
        system_prompt = SYSTEM_PROMPTS.get("abstract", "You are an academic author.")
        
        prompt = PROMPT_TEMPLATES["abstract_generation"].format(
            problem_statement=inputs["problem_statement"],
            methodology_summary=inputs["methodology_summary"],
            implementation_summary=inputs["implementation_summary"],
            results_summary=inputs["results_summary"],
            key_contributions=inputs["key_contributions"],
            limitations=inputs["limitations"]
        )
        
        # Single Pass - No expansion loop needed for abstract
        section["compilation_phase"] = "SYNTHESIZING"

        abstract_content = self._generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            phase=CompilationPhase.ABSTRACT,
            temperature=0.3
        )
        
        section["compilation_phase"] = "COMPLETE"
        return abstract_content

    def _build_abstract_inputs(self) -> Dict[str, str]:
        """
        Extracts summary content from specific accepted chapters.
        """
        sections = self.state.get("sections", [])
        
        def get_text(sid: str, default: str = "N/A") -> str:
            sec = next((s for s in sections if s["section_id"] == sid), None)
            if not sec or not sec.get("content"):
                return default
            return sec["content"]

        # Intelligent Extraction (Heuristics)
        # We try to grab the first 300 words if the section is huge, 
        # or specific subsections if identifiable.
        
        # Chapter 1: Intro -> Problem Statement
        # Ideally extract "1.3 Problem Statement"
        c1_text = get_text("chapter_1", "Problem statement not found.")
        problem_val = self._extract_subsection(c1_text, "Problem Statement") or self._truncate_words(c1_text, 300)
        
        # Chapter 4: Methodology -> Proposed System
        c4_text = get_text("chapter_4", "Methodology not found.")
        method_val = self._extract_subsection(c4_text, "Proposed System") or self._truncate_words(c4_text, 300)

        # Chapter 6: Implementation -> System Flow
        c6_text = get_text("chapter_6", "Implementation detailed not found.")
        impl_val = self._extract_subsection(c6_text, "Implemented System Flow") or self._truncate_words(c6_text, 300)
        
        # Chapter 8: Results -> Performance or Conclusion
        c8_text = get_text("chapter_8", "Results not found.")
        results_val = self._extract_subsection(c8_text, "Performance Analysis") or self._truncate_words(c8_text, 300)
        
        # Chapter 9: Conclusion
        c9_text = get_text("chapter_9", "Conclusion not found.")
        
        # Key Contributions: Often in Intro or Methodology. 
        # Let's use the 'Advantages' from Ch 4 if available
        contrib_val = self._extract_subsection(c4_text, "Advantages")
        if not contrib_val:
            contrib_val = (
                "- Hybrid LLM-based report compilation architecture\n"
                "- Deterministic multi-pass section expansion\n"
                "- Cost-efficient academic report generation pipeline"
            )
        
        # Limitations: From Ch 2 (Gaps) or Ch 9 (Future Scope/Limitation)
        # Ch 10 is Future Scope.
        gap_data = self.state.get("research_gaps", [])
        gaps_str = "\n".join([g.get("rationale", "") for g in gap_data[:3]])
        
        return {
            "problem_statement": problem_val,
            "methodology_summary": method_val,
            "implementation_summary": impl_val,
            "results_summary": results_val,
            "key_contributions": contrib_val,
            "limitations": gaps_str or "No critical limitations noted."
        }
    
    def _truncate_words(self, text: str, max_words: int = 300) -> str:
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]) + "..."
        
    def _extract_subsection(self, text: str, header_keyword: str) -> Optional[str]:
        """
        Attempts to find a Markdown header containing the keyword and returns its content
        until the next header of same or higher level.
        """
        lines = text.splitlines()
        capturing = False
        content = []
        base_level = 0
        
        for line in lines:
            if line.strip().startswith("#"):
                # Header detected
                level = len(line) - len(line.lstrip("#"))
                clean_header = line.lstrip("#").strip().lower()
                
                if capturing:
                    # If we hit another header of same or higher level (fewer #s), stop.
                    if level <= base_level:
                        break
                    
                if header_keyword.lower() in clean_header:
                    capturing = True
                    base_level = level
                    continue # Skip the header line itself? Or keep usage? User said no headers? usage?
                    # The prompt asks for INPUT: Summary. 
                    # Providing the text without the header is cleaner.
            
            if capturing:
                content.append(line)
                
        if content:
            return "\n".join(content).strip()
        return None

