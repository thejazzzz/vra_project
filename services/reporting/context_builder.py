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
            
        # Literature & Summaries
        papers = state.get("selected_papers", [])[:10]
        if papers:
            paper_lines = []
            for p in papers:
                title = p.get('title', 'Unknown')
                summary = state.get("paper_summaries", {}).get(p.get("paper_id"), p.get("abstract", ""))
                if summary:
                    paper_lines.append(f"- {title}: {summary}")
            facts["literature_context"] = "\n".join(paper_lines)
            
        # Gaps
        gaps = state.get("research_gaps", [])
        if gaps:
            gap_lines = [f"- {g.get('description', '')} ({g.get('rationale', '')})" for g in gaps[:5]]
            facts["identified_gaps"] = "\n".join(gap_lines)
            
        # Trends
        trends = state.get("concept_trends", {}).get("trends", {})
        if trends:
            sorted_trends = sorted(trends.items(), key=lambda x: x[1].get("total_count", 0), reverse=True)[:10]
            trend_lines = [f"- {k}: {v.get('status', 'Unknown')} (Growth: {v.get('growth_rate', 0)})" for k, v in sorted_trends]
            facts["concept_trends"] = "\n".join(trend_lines)

        return {**base_context, **facts}
