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
    def build_context(section_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        
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
                "provenance_stats": f"Papers: {len(papers)}. Edges: {meta.get('edges_present', 0)}",
                "data_warnings": "\n".join(warnings)
                if warnings else "None."
            }

        return {}
