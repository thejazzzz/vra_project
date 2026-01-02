#File:  services/reporting/section_planner.py
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import hashlib
import json
import datetime
import uuid

from state.state_schema import ReportState, ReportSectionState, SectionHistory

@dataclass
class ReportSection:
    section_id: str
    title: str
    description: str
    required_data: List[str] # Keys in state/context needed
    template_key: str # Key for the prompt template
    depends_on: List[str] = field(default_factory=list) # IDs of sections that must be ACCEPTED
    subsections: List['ReportSection'] = field(default_factory=list) # Hierarchical decomposition

class SectionPlanner:
    """
    Deterministically plans the report structure based on available data.
    Supports hierarchical decomposition and dependency tracking.
    """

    @staticmethod
    def plan_report(state: Dict[str, Any]) -> List[ReportSection]:
        """
        Plans the report structure.
        """
        sections = []

        def has_required_data(keys: List[str]) -> bool:
            """Check if all key sources exist in state."""
            return all(key in state for key in keys)
        
        # 1. Trend Analysis
        trends = state.get("concept_trends", {}).get("trends", {})
        trend_reqs = ["concept_trends"]
        trend_section_id = None
        if trends and has_required_data(trend_reqs):
            trend_section_id = "trend_analysis"
            sections.append(ReportSection(
                section_id=trend_section_id,
                title="Trend Analysis",
                description="Analysis of temporal evolution and concept stability.",
                required_data=trend_reqs,
                template_key="trend_analysis"
            ))

        # 2. Gap Analysis
        gaps = state.get("research_gaps", [])
        gap_reqs = ["research_gaps"]
        gap_section_id = None
        if gaps and has_required_data(gap_reqs):
            gap_section_id = "gap_analysis"
            sections.append(ReportSection(
                section_id=gap_section_id,
                title="Research Gaps & Opportunities",
                description="Identification of under-explored areas and structural holes.",
                required_data=gap_reqs,
                template_key="gap_analysis"
            ))

        # 3. Network/Author Analysis
        ag = state.get("author_graph", {})
        net_reqs = ["author_graph"]
        net_section_id = None
        if ag and ag.get("meta", {}).get("edges_present") and has_required_data(net_reqs):
            net_section_id = "network_analysis"
            sections.append(ReportSection(
                section_id=net_section_id,
                title="Collaboration Network Analysis",
                description="Insights into author influence and community structure.",
                required_data=net_reqs,
                template_key="network_analysis"
            ))

        # 4. Methodological Limitations
        limit_reqs = ["selected_papers", "author_graph"]
        limit_section_id = None
        if has_required_data(limit_reqs):
            limit_section_id = "limitations"
            sections.append(ReportSection(
                section_id=limit_section_id,
                title="Methodology & Limitations",
                description="Statement of data scope, provenance, and metric validity.",
                required_data=limit_reqs,
                template_key="limitations"
            ))
            
        # 5. Executive Summary (Depends on Analysis Sections)
        # It should come FIRST in the document, but depend on others.
        # However, for UX, we might want to generate it last, but show it first?
        # The user's prompt implies "sequencing".
        # We will insert it at the TOP of the list for display, but set dependencies.
        exec_reqs = ["query"]
        if has_required_data(exec_reqs):
            # Calculate deps
            # Exec summary depends on all analytical sections found
            exec_deps = []
            if trend_section_id: exec_deps.append(trend_section_id)
            if gap_section_id: exec_deps.append(gap_section_id)
            if net_section_id: exec_deps.append(net_section_id)
            if limit_section_id: exec_deps.append(limit_section_id)

            sections.insert(0, ReportSection(
                section_id="exec_summary",
                title="Executive Summary",
                description="High-level overview of the research landscape.",
                required_data=exec_reqs,
                template_key="executive_summary",
                depends_on=exec_deps
            ))

        # 6. Evidence Appendix (Deterministic)
        sections.append(ReportSection(
            section_id="appendix",
            title="Evidence Appendix",
            description="Deterministic data tables.",
            required_data=[],
            template_key="deterministic_appendix"
        ))

        return sections

    @staticmethod
    def initialize_report_state(state: Dict[str, Any]) -> ReportState:
        """
        Creates the initial ReportState from the plan.
        """
        planned_sections = SectionPlanner.plan_report(state)
        
        # Convert to ReportSectionState
        section_states: List[ReportSectionState] = []
        for p in planned_sections:
            s_state: ReportSectionState = {
                "section_id": p.section_id,
                "status": "planned",
                "title": p.title,
                "description": p.description,
                "depends_on": p.depends_on,
                "template_key": p.template_key,
                "content": None,
                "revision": 0,
                "max_revisions": 3,
                "history": [],
                "quality_scores": None
            }
            section_states.append(s_state)
            
        # Calculate Order Hash
        # We use section_id + title + depends_on to signature the order
        order_signature = [
            f"{s['section_id']}:{s['title']}:{sorted(s['depends_on'])}" 
            for s in section_states
        ]
        order_hash = hashlib.sha256(json.dumps(order_signature).encode()).hexdigest()
        
        initial_state: ReportState = {
            "report_status": "planned",
            "sections": section_states,
            "locks": {
                "report": False,
                "sections": {s["section_id"]: False for s in section_states}
            },
            "last_successful_step": None,
            "section_order_hash": order_hash,
            "user_confirmed_start": False, # Requires explicit confirm
            "user_confirmed_finalize": False,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "metrics": {
                "generation_count": 0,
                "total_revisions": 0
            }
        }
        
        return initial_state

