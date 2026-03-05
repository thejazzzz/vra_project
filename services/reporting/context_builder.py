#File: services/reporting/context_builder.py
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class ContextBuilder:
    """
    Slices global state into specific contexts for each section.
    Minimizes token usage and focus hallucination risk.
    """

    @staticmethod
    def get_tone(audience: str) -> str:
        return {
            "phd": "formal, technical, citation-heavy, academic",
            "rd": "technical, pragmatic, implementation-focused, engineering-centric",
            "industry": "strategic, concise, business-oriented, ROI-focused",
            "general": "neutral, informative, accessible"
        }.get(audience, "neutral, informative")

    @staticmethod
    def get_depth(audience: str) -> str:
        return {
            "phd": "comprehensive, theoretical, methodological deep-dive",
            "rd": "architectural, system-design focused, feasibility-oriented",
            "industry": "high-level, executive summary style, key takeaways",
            "general": "overview, balanced"
        }.get(audience, "balanced")

    @staticmethod
    def get_focus(audience: str) -> str:
        return {
            "phd": "novelty, limitations, future work, validity",
            "rd": "scalability, performance, integration, tech stack",
            "industry": "market impact, risks, opportunities, cost-benefit",
            "general": "main concepts, general trends"
        }.get(audience, "general trends")

    @staticmethod
    def get_section_constraints(section_id: str, audience: str) -> str:
        """
        Returns hard formatting/content constraints based on audience and section.
        """
        constraints = []
        
        if section_id == "gap_analysis":
            if audience == "industry":
                constraints = [
                    "- Limit to 5 high-impact opportunities.",
                    "- Each point MUST mention business impact, ROI, or competitive advantage.",
                    "- Avoid theoretical gaps; focus on applied opportunities."
                ]
            elif audience == "phd":
                constraints = [
                    "- Focus on theoretical and methodological gaps.",
                    "- Relate gaps to specific limitations in cited papers.",
                    "- Propose formal future research directions."
                ]
            elif audience == "rd":
                constraints = [
                    "- Focus on implementation challenges and system bottlenecks.",
                    "- Propose architectural or engineering improvements.",
                    "- Assess feasibility of closing these gaps."
                ]
        elif section_id == "exec_summary":
             if audience == "industry":
                constraints.append("- MUST end with a 'Strategic Recommendation' sentence.")
             elif audience == "phd":
                constraints.append("- MUST end with a 'Contribution to Field' statement.")

        return "\n".join(constraints) if constraints else "None."

    @staticmethod
    def build_context(section_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        
        # Audience Logic
        audience = state.get("audience", "industry")
        if "audience" not in state:
             logger.warning("Audience missing from state in ContextBuilder, defaulting to 'industry'")

        base_context = {
            "audience": audience,
            "tone": ContextBuilder.get_tone(audience),
            "depth": ContextBuilder.get_depth(audience),
            "focus": ContextBuilder.get_focus(audience),
            "constraints": ContextBuilder.get_section_constraints(section_id, audience)
        }

        # Common Metadata
        query = state.get("query", "Unknown Topic")
        
        # --- NEW LOGIC: Provide universal rich context for all chapters ---
        facts = {"query": query}
        
        # Global themes
        ga = state.get("global_analysis", {})
        if ga:
            facts["global_themes"] = str(ga.get("themes", "None"))
            if "executive_summary" in ga:
                facts["executive_summary"] = str(ga.get("executive_summary", "None"))
            
        report_state = state.get("report_state", {})
        sections = report_state.get("sections", [])
        
        current_sec = next((s for s in sections if s.get("section_id") == section_id), {})
        sec_title = current_sec.get("title", "").lower()
        sec_type = current_sec.get("section_type", "").lower()

        is_intro = "intro" in sec_type or "background" in sec_type or "introduction" in sec_title or "abstract" in sec_title
        is_lit = "lit" in sec_type or "review" in sec_type or "overview" in sec_title
        is_method = "method" in sec_type or "design" in sec_type or "dataset" in sec_title
        is_analysis = "analysis" in sec_type or "result" in sec_type or any(k in sec_title for k in ["graph", "trend", "gap", "hypothesis", "discussion"])
        is_conclusion = "conclusion" in sec_type or "future" in sec_type or "summary" in sec_title

        # Papers & Summaries (Crucial for Lit/Method)
        papers = state.get("selected_papers", [])[:10]
        if papers and (is_intro or is_lit or is_method or not any([is_intro, is_lit, is_method, is_analysis, is_conclusion])):
            paper_lines = []
            for p in papers:
                title = p.get('title', 'Unknown')
                summary = state.get("paper_summaries", {}).get(p.get("paper_id"), p.get("abstract", ""))
                if summary:
                    paper_lines.append(f"- {title}: {summary}")
            facts["literature_context"] = "\n".join(paper_lines)
            
        # Graph Analytics (Crucial for Analysis/Lit)
        citation_metrics = state.get("citation_metrics", {})
        if citation_metrics and (is_analysis or is_lit):
            facts["citation_velocity_and_pagerank"] = str(citation_metrics)

        # Gaps (Crucial for Analysis/Conclusion/Intro)
        gaps = state.get("research_gaps", [])
        if gaps and (is_analysis or is_conclusion or is_intro):
            gap_lines = [f"- {g.get('description', '')} ({g.get('rationale', '')})" for g in gaps[:5]]
            facts["identified_gaps"] = "\n".join(gap_lines)
            
        # Trends (Crucial for Intro/Analysis)
        trends = state.get("concept_trends", {}).get("trends", {})
        if trends and (is_intro or is_analysis):
            sorted_trends = sorted(trends.items(), key=lambda x: x[1].get("total_count", 0), reverse=True)[:10]
            trend_lines = [f"- {k}: {v.get('status', 'Unknown')} (Growth: {v.get('growth_rate', 0)})" for k, v in sorted_trends]
            facts["concept_trends"] = "\n".join(trend_lines)

        # --- NEW LOGIC: Rolling Context Memory ---
        previous_summaries = []
        
        for sec in sections:
            if sec.get("status") == "accepted" and sec.get("section_id") != section_id and sec.get("content"):
                # Very simple extraction: grab first 100 words of the accepted section to serve as a memory hint
                words = sec["content"].split()
                snippet = " ".join(words[:100]) + ("..." if len(words) > 100 else "")
                label = sec.get('title') or sec.get('section_id') or 'Unknown Section'
                previous_summaries.append(f"[{label}]:\n{snippet}")

        if previous_summaries:
            facts["previously_written_sections_summary"] = "\n\n".join(previous_summaries)
        return {**base_context, **facts}
