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
        
        if section_id == "exec_summary":
            # Extract high-level summaries only
            trends = state.get("concept_trends", {}).get("trends", {})
            sorted_trends = sorted(trends.items(), key=lambda x: x[1].get("total_count", 0), reverse=True)[:5]
            trend_summary = ", ".join([f"{k} ({v.get('status', 'Unknown')})" for k, v in sorted_trends])
            
            gaps = state.get("research_gaps", [])
            gap_summary = f"{len(gaps)} gaps identified."
            if gaps:
                gap_summary += f" Top gap: {gaps[0].get('description')}"

            return {
                **base_context,
                "query": query,
                "trend_summary": trend_summary,
                "gap_summary": gap_summary
            }

        elif section_id == "trend_analysis":
            # Tabular data for trends
            trends_data = state.get("concept_trends", {}).get("trends", {})
            # Textual representation for LLM
            lines = []
            for concept, data in trends_data.items():
                lines.append(
                    f"Concept: {concept} | Status: {data.get('status')} | "
                    f"Growth: {data.get('growth_rate')} | Stability: {data.get('stability')}"
                )
            return {
                **base_context,
                "query": query,
                "trends_table": "\n".join(lines)
            }

        elif section_id == "gap_analysis":
            # Detailed gap list
            gaps = state.get("research_gaps", [])
            lines = []
            for g in gaps:
                lines.append(
                    f"ID: {g.get('gap_id')} | Type: {g.get('type')} | "
                    f"Desc: {g.get('description')} | Rationale: {g.get('rationale')} | "
                    f"Confidence: {g.get('confidence')}"
                )
            return {
                **base_context,
                "query": query,
                "gaps_list": "\n".join(lines)
            }

        elif section_id == "network_analysis":
            ag = state.get("author_graph", {})
            nodes = ag.get("nodes", [])
            # Top 5 influencers
            top_nodes = sorted(nodes, key=lambda x: x.get("influence_score", 0), reverse=True)[:5]
            authors = [f"{n.get('id', 'Unknown')} (Score: {n.get('influence_score', 0)})" for n in top_nodes]

            
            
            return {
                **base_context,
                "query": query,
                "author_stats": ", ".join(authors),
                "diversity_index": ag.get("meta", {}).get("diversity_index", "N/A")
            }
        elif section_id == "limitations":
            ag = state.get("author_graph", {})
            meta = ag.get("meta", {})
            valid = meta.get("metrics_valid", False)
            
            warnings = []
            if not valid:
                warnings.append("Metrics are heuristic due to sparse data or lack of edges.")
            if meta.get("warning"):
                warnings.append(meta.get("warning"))
                
            papers = state.get("selected_papers", [])
            
            return {
                **base_context,
                "provenance_stats": f"Papers: {len(papers)}. Edges: {meta.get('edges_present', 0)}",
                "data_warnings": "\n".join(warnings)
                if warnings else "None."
            }

        return {}
