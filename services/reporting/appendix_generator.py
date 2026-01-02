#File: services/reporting/appendix_generator.py
from typing import Dict, Any, List

class AppendixGenerator:
    """
    Deterministically renders evidence appendices without LLM usage.
    Ensures 100% provenance and reduces token costs.
    """

    @staticmethod
    def generate_appendix(state: Dict[str, Any]) -> str:
        parts = ["# Appendix A: Evidence & Provenance\n"]
        
        # 1. Trend Evidence
        trends = state.get("concept_trends", {}).get("trends", {})
        if trends:
            parts.append("## A.1 Trend Evidence\n")
            parts.append("| Concept | Status | Key Papers (IDs) |")
            parts.append("|---|---|---|")
            for concept, data in trends.items():
                pids = ", ".join(data.get("paper_ids", [])[:5]) # Top 5 IDs
                parts.append(f"| {concept} | {data.get('status','N/A')} | {pids} |")
            parts.append("\n")

        # 2. Gap Evidence
        gaps = state.get("research_gaps", [])
        if gaps:
            parts.append("## A.2 Research Gaps Rationale\n")
            parts.append("| Gap ID | Type | Rationale | Confidence |")
            parts.append("|---|---|---|---|")
            for gap in gaps:
                parts.append(f"| {gap.get('gap_id','N/A')} | {gap.get('type','N/A')} | {gap.get('rationale','N/A')} | {gap.get('confidence','N/A')} |")
            parts.append("\n")

        # 3. Validated Bibliography (Authors)
        ag = state.get("author_graph", {})
        nodes = ag.get("nodes", [])
        if nodes:
            parts.append("## A.3 Influential Authors Mapped\n")
            parts.append("| Author | Influence Score | Dominance |")
            parts.append("|---|---|---|")
            # Sort by influence
            sorted_nodes = sorted(
                nodes, 
                key=lambda x: x.get("influence_score", 0) if isinstance(x.get("influence_score"), (int, float)) else 0, 
                reverse=True
            )[:20]            
            for n in sorted_nodes:
                parts.append(f"| {n.get('id','Unknown')} | {n.get('influence_score',0)} | {n.get('dominance','N/A')} |")
            parts.append("\n")

        return "\n".join(parts)
