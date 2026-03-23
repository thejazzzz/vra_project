# File: services/reporting/section_planner.py
from typing import List, Dict, Any, Optional, TypedDict
from dataclasses import dataclass, field
import hashlib
import json
import datetime
import uuid
import logging
import os

from state.state_schema import ReportState, ReportSectionState, SectionHistory, SectionType
from services.structured_llm import StructuredLLMService, SchemaModel
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# --- Pydantic Models for LLM Output ---

class ReportSectionPlan(BaseModel):
    section_index: str = Field(..., description="1.1, 1.2, etc.")
    title: str
    description: str
    section_type: str = Field(..., description="INTRO, LITERATURE, ANALYSIS, etc.")
    estimated_pages: float = Field(..., description="Estimated pages for this section")
    outline_points: List[str] = Field(..., description="List of bullet points for section content")

class ChapterPlan(BaseModel):
    chapter_number: int
    title: str
    sections: List[ReportSectionPlan]

class GlobalReportPlan(BaseModel):
    chapters: List[ChapterPlan]
    research_gaps: List[str] = Field(..., description="Identified research gaps")
    executive_summary_points: List[str] = Field(..., description="Key points for executive summary")

# ---------------------------------------------

@dataclass
class ReportSection:
    section_id: str
    title: str
    description: str
    required_data: List[str]
    template_key: str
    depends_on: List[str] = field(default_factory=list)
    
    # New Fields
    chapter_index: int = 1
    section_index: str = "1.0"
    section_type: SectionType = "ANALYSIS"
    target_words: int = 500
    compilation_phase: str = "PLANNED"
    subsections: List['ReportSection'] = field(default_factory=list)
    outline: List[str] = field(default_factory=list)

class SectionPlanner:
    """
    Deterministically plans the report structure.
    Phase 3.2 Upgrade: Uses 'Software Project Thesis' structure.
    """

    @staticmethod
    def _calculate_target_words(pages: float, section_type: str) -> int:
        """Type-Aware Word Budgeting"""
        BASE_WORDS_PER_PAGE = 500 # Adjusted base
        
        # Multipliers based on User Feedback and Standard Academic Density
        MULTIPLIERS: Dict[str, float] = {
            "INTRO": 1.5,
            "LITERATURE": 3.0,
            "ANALYSIS": 2.5,
            "METHODOLOGY": 3.0,
            "DESIGN": 2.0,     # Heavily diagrammatic, less prose? Or high spec? 
                              # User example has usage diagrams etc. Specs need words.
            "IMPLEMENTATION": 3.0,
            "TESTING": 2.0,
            "RESULTS": 2.0,
            "CONCLUSION": 1.0,
            "REFERENCE": 0.0,
            "APPENDIX": 0.0
        }
        
        mult = MULTIPLIERS.get(section_type, 2.0)
        # Avoid zero target
        if mult == 0: return 0 
        
        return int(pages * BASE_WORDS_PER_PAGE * mult)

    @staticmethod
    def plan_report(state: Dict[str, Any]) -> List[ReportSection]:
        """
        Plans the strict 'Software Project Thesis' structure.
        """
        sections: List[ReportSection] = []
        
        # --- Abstract / Exec Summary (Before Chapter 1) ---
        sections.append(ReportSection(
            section_id="abstract",
            title="Abstract",
            description="Concise synthesis of the entire report (Generated Last).",
            required_data=["generated_chapters"],
            template_key="abstract_generation",
            target_words=300, # Fixed budget
            section_type="INTRO",
            section_index="0.0",
            chapter_index=0,
            outline=["Problem", "Methodology", "Results", "Contribution"],
            depends_on=["chapter_1", "chapter_4", "chapter_6", "chapter_8", "chapter_9"]
        ))
        
        # --- Chapter 1: Introduction ---
        sections.append(ReportSection(
            section_id="chapter_1",
            title="Chapter 1: Introduction",
            description="Background, importance, motivation, and scope.",
            required_data=["query"],
            target_words=SectionPlanner._calculate_target_words(1.5, "INTRO"),
            template_key="draft_skeleton",
            section_type="INTRO",
            section_index="1.0",
            chapter_index=1,
            outline=[
                "1.1 Background of the Research Topic",
                "1.2 Importance of the Problem Domain", 
                "1.3 Motivation for Analysis",
                "1.4 Scope of the Analysis"
            ]
        ))
        
        # --- Chapter 2: Dataset and Source Collection ---
        sections.append(ReportSection(
            section_id="chapter_2",
            title="Chapter 2: Dataset and Source Collection",
            description="Overview of the search queries, sources, and paper filtering process.",
            required_data=["selected_papers"],
            template_key="draft_skeleton",
            target_words=SectionPlanner._calculate_target_words(1.5, "METHODOLOGY"),
            section_type="METHODOLOGY",
            section_index="2.0",
            chapter_index=2,
            outline=[
                "2.1 Queries and Search Strategy",
                "2.2 Data Sources",
                "2.3 Retrieval and Filtering Process",
                "2.4 Dataset Characteristics"
            ]
        ))

        # --- Chapter 3: Literature Overview ---
        lit_outline = []
        paper_titles = [p.get("title", "Unknown Paper") for p in state.get("selected_papers", [])[:5] if isinstance(p, dict)]
        if paper_titles:
            for i, p_title in enumerate(paper_titles, 1):
                lit_outline.append(f"3.{i} {p_title}")
        else:
            lit_outline = ["3.1 Summary of Relevant Papers", "3.2 Key Contributions", "3.3 Thematic Categorization"]

        sections.append(ReportSection(
            section_id="chapter_3",
            title="Chapter 3: Literature Overview",
            description="Summary of the most relevant papers and their key contributions.",
            required_data=["selected_papers", "paper_summaries"],
            template_key="draft_skeleton",
            target_words=SectionPlanner._calculate_target_words(3.0, "LITERATURE"),
            section_type="LITERATURE",
            section_index="3.0",
            chapter_index=3,
            outline=lit_outline
        ))

        # --- Chapter 4: Knowledge Graph Analysis ---
        sections.append(ReportSection(
            section_id="chapter_4",
            title="Chapter 4: Knowledge Graph Analysis",
            description="Insights from citation networks, connectivity, and author collaborations.",
            required_data=["citation_metrics"],
            template_key="draft_skeleton",
            target_words=SectionPlanner._calculate_target_words(2.0, "ANALYSIS"),
            section_type="ANALYSIS",
            section_index="4.0",
            chapter_index=4,
            outline=[
                "4.1 Knowledge Graph Construction",
                "4.2 Citation Network Insights",
                "4.3 Author Collaboration Patterns",
                "4.4 Influential Nodes and Clusters"
            ]
        ))

        # --- Chapter 5: Trend Analysis ---
        sections.append(ReportSection(
            section_id="chapter_5",
            title="Chapter 5: Trend Analysis",
            description="Emerging research trends, popular methodologies, and evolution of the topic.",
            required_data=["concept_trends"],
            template_key="draft_skeleton",
            target_words=SectionPlanner._calculate_target_words(2.0, "ANALYSIS"),
            section_type="ANALYSIS",
            section_index="5.0",
            chapter_index=5,
            outline=[
                "5.1 Emerging Research Trends",
                "5.2 Popular Methodologies",
                "5.3 Technical Evolution Over Time",
                "5.4 Frequently Studied Subtopics"
            ]
        ))

        # --- Chapter 6: Research Gaps ---
        sections.append(ReportSection(
            section_id="chapter_6",
            title="Chapter 6: Research Gaps",
            description="Underexplored areas, limitations, and opportunities for improvement.",
            required_data=["research_gaps"],
            template_key="draft_skeleton",
            target_words=SectionPlanner._calculate_target_words(2.0, "ANALYSIS"),
            section_type="ANALYSIS",
            section_index="6.0",
            chapter_index=6,
            outline=[
                "6.1 Underexplored Research Areas",
                "6.2 Limitations of Current Approaches",
                "6.3 Missing Datasets or Evaluation Methods",
                "6.4 Opportunities for Improvement"
            ]
        ))

        # --- Chapter 7: Generated Research Hypotheses ---
        sections.append(ReportSection(
            section_id="chapter_7",
            title="Chapter 7: Generated Research Hypotheses",
            description="Proposed research directions and potential experimental setups based on detected gaps.",
            required_data=["research_gaps"],
            template_key="draft_skeleton",
            target_words=SectionPlanner._calculate_target_words(1.5, "ANALYSIS"),
            section_type="ANALYSIS",
            section_index="7.0",
            chapter_index=7,
            outline=[
                "7.1 Proposed Research Directions",
                "7.2 Hypotheses from Existing Literature",
                "7.3 Potential Experimental Setups"
            ]
        ))

        # --- Chapter 8: Discussion ---
        sections.append(ReportSection(
            section_id="chapter_8",
            title="Chapter 8: Discussion",
            description="Interpretation of insights, relationship between trends and gaps, and implications.",
            required_data=["concept_trends", "research_gaps", "citation_metrics"],
            depends_on=["chapter_4", "chapter_5", "chapter_6", "chapter_7"],
            template_key="draft_skeleton",
            target_words=SectionPlanner._calculate_target_words(1.5, "RESULTS"),
            section_type="RESULTS",
            section_index="8.0",
            chapter_index=8,
            outline=[
                "8.1 Interpretation of Insights",
                "8.2 Relationship Between Trends and Gaps",
                "8.3 Implications for Future Research"
            ]
        ))

        # --- Chapter 9: Conclusion ---
        sections.append(ReportSection(
            section_id="chapter_9",
            title="Chapter 9: Conclusion",
            description="Summary of key findings and overall insights derived from the literature.",
            required_data=[],
            depends_on=["chapter_1", "chapter_8"],
            template_key="draft_skeleton",
            target_words=SectionPlanner._calculate_target_words(1.0, "CONCLUSION"),
            section_type="CONCLUSION",
            section_index="9.0",
            chapter_index=9,
            outline=[
                "9.1 Summary of Key Findings",
                "9.2 Final Remarks"
            ]
        ))
        
        # --- Evidence Appendix ---
        sections.append(ReportSection(
            section_id="appendix",
            title="Evidence Appendix",
            description="Appendix and References.",
            required_data=[],
            template_key="deterministic_appendix",
            target_words=SectionPlanner._calculate_target_words(0, "APPENDIX"),
            section_type="APPENDIX",
            section_index="11.0",
            chapter_index=11,
            outline=[]
        ))

        return sections

    @staticmethod
    def get_template_key(state: Dict[str, Any], section_id: str) -> Optional[str]:
        # Simple lookup fallback
        if section_id.startswith("chapter_"): return "draft_skeleton"
        if section_id == "abstract": return "abstract_generation"
        if section_id == "appendix": return "deterministic_appendix"
        return "draft_skeleton"

    @staticmethod
    def initialize_report_state(state: Dict[str, Any]) -> ReportState:
        planned_sections = SectionPlanner.plan_report(state)
        
        section_states: List[ReportSectionState] = []
        for p in planned_sections:
            s_state: ReportSectionState = {
                "section_id": p.section_id,
                "status": "planned",
                "title": p.title,
                "description": p.description,
                "depends_on": p.depends_on,
                "template_key": p.template_key,
                
                "chapter_index": p.chapter_index,
                "section_index": p.section_index,
                "section_type": p.section_type,
                "target_words": p.target_words,
                "current_words": 0,
                "compilation_phase": "PLANNED",
                "subsections": [],
                
                "content": None,
                "revision": 0,
                "max_revisions": 3,
                "history": [],
                "quality_scores": None
            }
            # Add outline to description for context if needed, or pass explicitly later
            # For now, we rely on the Compiler simulating the outline from the title if not explicitly passed.
            # WAIT: We need to store the outline in ReportSectionState so Compiler can use it!
            # Adding 'outline' to ReportSectionState logic via 'description' hack or just trusting Compiler to regenerate.
            # BETTER: Append outline to description so it's visible to LLM.
            if p.outline:
                s_state["description"] += "\n\nREQUIRED OUTLINE:\n" + "\n".join(f"- {o}" for o in p.outline)

            section_states.append(s_state)
            
        order_signature = [f"{s['section_id']}" for s in section_states]
        order_hash = hashlib.sha256(json.dumps(order_signature).encode()).hexdigest()
        
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        
        initial_state: ReportState = {
            "report_status": "planned",
            "sections": section_states,
            "locks": {
                "report": False,
                "sections": {s["section_id"]: False for s in section_states}
            },
            "last_successful_step": None,
            "section_order_hash": order_hash,
            "user_confirmed_start": False,
            "user_confirmed_finalize": False,
            "created_at": utc_now.isoformat(),
            "updated_at": utc_now.isoformat(),
            "metrics": {
                "generation_count": 0,
                "total_revisions": 0,
                "cloud_calls": 0
            }
        }
        
        return initial_state
