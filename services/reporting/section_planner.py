#File:  services/reporting/section_planner.py
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class ReportSection:
    section_id: str
    title: str
    description: str
    required_data: List[str] # Keys in state/context needed
    template_key: str # Key for the prompt template
    subsections: List['ReportSection'] = field(default_factory=list) # Hierarchical decomposition

class SectionPlanner:
    """
    Deterministically plans the report structure based on available data.
    Supports hierarchical decomposition for scalability.
    """

    @staticmethod
    def plan_report(state: Dict[str, Any]) -> List[ReportSection]:
        """
        Plans the report structure.
        
        ARCHITECTURE NOTE - TWO-STAGE DATA VALIDATION:
        1. Source Validation (Here): Checks if raw 'Source Keys' (e.g. 'concept_trends') exist in state.
           If missing, the section is skipped entirely.
        2. Context Transformation (ContextBuilder): Transforms 'Source Keys' into 'Template Keys' (e.g. 'trends_table').
           The required_data fields below reference the SOURCE KEYS to ensure this planner is self-consistent
           and checks the actual available state.
        """
        sections = []

        def has_required_data(keys: List[str]) -> bool:
            """Check if all key sources exist in state."""
            return all(key in state for key in keys)

        # 1. Executive Summary (Conditional: requires query)
        # Note: 'trend_summary' and 'gap_summary' are derived by ContextBuilder from concept_trends/research_gaps.
        # We generally expect 'query' to exist.
        exec_reqs = ["query"]
        if has_required_data(exec_reqs):
            sections.append(ReportSection(
                section_id="exec_summary",
                title="Executive Summary",
                description="High-level overview of the research landscape.",
                required_data=exec_reqs,
                template_key="executive_summary"
            ))

        # 2. Trend Analysis (Condition: Trends found)
        # Check if concept_trends exists in state
        trends = state.get("concept_trends", {}).get("trends", {})
        trend_reqs = ["concept_trends"]
        if trends and has_required_data(trend_reqs):
            # Hierarchical check: If > 5 trends, split? For now, keep flat but ready for split.
            sections.append(ReportSection(
                section_id="trend_analysis",
                title="Trend Analysis",
                description="Analysis of temporal evolution and concept stability.",
                required_data=trend_reqs,
                template_key="trend_analysis"
            ))

        # 3. Gap Analysis (Condition: Gaps found)
        gaps = state.get("research_gaps", [])
        gap_reqs = ["research_gaps"]
        if gaps and has_required_data(gap_reqs):
            sections.append(ReportSection(
                section_id="gap_analysis",
                title="Research Gaps & Opportunities",
                description="Identification of under-explored areas and structural holes.",
                required_data=gap_reqs,
                template_key="gap_analysis"
            ))

        # 4. Network/Author Analysis (Condition: Author Graph exists)
        ag = state.get("author_graph", {})
        net_reqs = ["author_graph"]
        if ag and ag.get("meta", {}).get("edges_present") and has_required_data(net_reqs):
            sections.append(ReportSection(
                section_id="network_analysis",
                title="Collaboration Network Analysis",
                description="Insights into author influence and community structure.",
                required_data=net_reqs,
                template_key="network_analysis"
            ))

        # 5. Methodological Limitations (Conditional: requires provenance data)
        # Derived from 'selected_papers' and 'author_graph'
        limit_reqs = ["selected_papers", "author_graph"]
        if has_required_data(limit_reqs):
            sections.append(ReportSection(
                section_id="limitations",
                title="Methodology & Limitations",
                description="Statement of data scope, provenance, and metric validity.",
                required_data=limit_reqs,
                template_key="limitations"
            ))
        
        # 6. Evidence Appendix (Deterministic)
        # Always add, as it handles empty states gracefully internally.
        sections.append(ReportSection(
            section_id="appendix",
            title="Evidence Appendix",
            description="Deterministic data tables.",
            required_data=[],
            template_key="deterministic_appendix"
        ))

        return sections
