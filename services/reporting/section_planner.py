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
        # 1.1 Background, 1.2 Existing System, 1.3 Problem Statement, 1.4 Objectives, 1.5 Scope
        sections.append(ReportSection(
            section_id="chapter_1",
            title="Chapter 1: Introduction",
            description="Background, problem statement, and objectives.",
            required_data=["query"],
            target_words=SectionPlanner._calculate_target_words(2.0, "INTRO"),
            template_key="draft_skeleton",
            section_type="INTRO",
            section_index="1.0",
            chapter_index=1,
            outline=[
                "1.1 Background",
                "1.2 Existing System", 
                "1.3 Problem Statement",
                "1.4 Objectives",
                "1.5 Scope"
            ]
        ))
        
        # --- Chapter 2: Literature Review ---
        # Dynamic papers integration
        lit_outline = []
        # Try to pull papers from state
        paper_titles = []
        if "selected_papers" in state:
            paper_titles = [
                p.get("title", "Unknown Paper") 
                for p in state["selected_papers"][:5] 
                if isinstance(p, dict)
            ]
        
        if paper_titles:
            for i, p_title in enumerate(paper_titles, 1):
                lit_outline.append(f"2.{i} {p_title}")
        else:
            lit_outline = ["2.1 AI-Powered Systems", "2.2 Related Work in LLMs", "2.3 Previous Approaches"]
            
        lit_outline.append(f"2.{len(lit_outline)+1} Research Gap")

        sections.append(ReportSection(
            section_id="chapter_2",
            title="Chapter 2: Literature Review",
            description="Review of existing works and identification of gaps.",
            required_data=["selected_papers"],
            template_key="draft_skeleton", # Reuse/Adapt
            target_words=SectionPlanner._calculate_target_words(4.0, "LITERATURE"),
            section_type="LITERATURE",
            section_index="2.0",
            chapter_index=2,
            outline=lit_outline
        ))

        # --- Chapter 3: System Analysis ---
        sections.append(ReportSection(
            section_id="chapter_3",
            title="Chapter 3: System Analysis",
            description="Feasibility and requirements analysis.",
            required_data=[],
            template_key="draft_skeleton", # Reuse analysis logic
            target_words=SectionPlanner._calculate_target_words(3.0, "ANALYSIS"),
            section_type="ANALYSIS",
            section_index="3.0",
            chapter_index=3,
            outline=[
                "3.1 Expected System Requirements",
                "3.2 Feasibility Analysis",
                "3.2.1 Technical Feasibility",
                "3.2.2 Operational Feasibility",
                "3.3 Economic Feasibility",
                "3.4 Software Requirements",
                "3.5 Hardware Requirements",
                "3.6 Software Cost Estimation",
                "3.7 Project Scheduling (Gantt)"
            ]
        ))

        # --- Chapter 4: Methodology ---
        sections.append(ReportSection(
            section_id="chapter_4",
            title="Chapter 4: Methodology",
            description="Algorithms and modular decomposition.",
            required_data=[],
            template_key="draft_skeleton",
            target_words=SectionPlanner._calculate_target_words(4.0, "METHODOLOGY"),
            section_type="METHODOLOGY",
            section_index="4.0",
            chapter_index=4,
            outline=[
                "4.1 Proposed System",
                "4.2 Modular Decomposition",
                "4.3 Algorithm",
                "4.3.1 Overall System Algorithm",
                "4.3.2 Agent Algorithms",
                "4.4 Advantages of Proposed System"
            ]
        ))

        # --- Chapter 5: System Design ---
        sections.append(ReportSection(
            section_id="chapter_5",
            title="Chapter 5: System Design",
            description="UML diagrams and architectural design.",
            required_data=[],
            template_key="draft_skeleton",
            target_words=SectionPlanner._calculate_target_words(3.0, "DESIGN"),
            section_type="DESIGN",
            section_index="5.0",
            chapter_index=5,
            outline=[
                "5.1 Flow Chart",
                "5.2 Use Case Diagram",
                "5.3 Activity Diagram",
                "5.4 Sequence Diagram",
                "5.5 Collaboration Diagram",
                "5.6 Architecture Diagram"
            ]
        ))

        # --- Chapter 6: System Implementation ---
        sections.append(ReportSection(
            section_id="chapter_6",
            title="Chapter 6: System Implementation",
            description="Details of the development process.",
            required_data=[],
            template_key="draft_skeleton",
            target_words=SectionPlanner._calculate_target_words(5.0, "IMPLEMENTATION"),
            section_type="IMPLEMENTATION",
            section_index="6.0",
            chapter_index=6,
            outline=[
                "6.1 Development Environment Setup",
                "6.2 Frontend Development",
                "6.3 Backend Development",
                "6.4 AI Agent Implementation",
                "6.5 Implemented System Flow"
            ]
        ))

        # --- Chapter 7: System Testing ---
        sections.append(ReportSection(
            section_id="chapter_7",
            title="Chapter 7: System Testing",
            description="Testing strategies and summary.",
            required_data=[],
            template_key="draft_skeleton",
            target_words=SectionPlanner._calculate_target_words(2.0, "TESTING"),
            section_type="TESTING",
            section_index="7.0",
            chapter_index=7,
            outline=[
                "7.1 Types of Testing (Unit, Integration, System)",
                "7.2 Test Cases",
                "7.3 Test Summary Report"
            ]
        ))

        # --- Chapter 8: Results ---
        sections.append(ReportSection(
            section_id="chapter_8",
            title="Chapter 8: Results",
            description="Performance analysis and metrics.",
            required_data=["concept_trends"], # Use trends as proxy for results if available
            template_key="draft_skeleton",
            target_words=SectionPlanner._calculate_target_words(2.0, "RESULTS"),
            section_type="RESULTS",
            section_index="8.0",
            chapter_index=8,
            outline=[
                "8.1 Performance Analysis",
                "8.2 Comparative Performance Table",
                "8.3 Qualitative Results"
            ]
        ))

        # --- Chapter 9: Conclusion ---
        sections.append(ReportSection(
            section_id="chapter_9",
            title="Chapter 9: Conclusion",
            description="Summary of achievements.",
            required_data=[],
            template_key="draft_skeleton",
            target_words=SectionPlanner._calculate_target_words(1.0, "CONCLUSION"),
            section_type="CONCLUSION",
            section_index="9.0",
            chapter_index=9,
            outline=["9.1 Conclusion"]
        ))
        
        # --- Chapter 10: Future Scope ---
        sections.append(ReportSection(
            section_id="chapter_10",
            title="Chapter 10: Future Scope",
            description="Future enhancements.",
            required_data=[],
            template_key="draft_skeleton",
            target_words=SectionPlanner._calculate_target_words(1.0, "CONCLUSION"),
            section_type="CONCLUSION",
            section_index="10.0",
            chapter_index=10,
            outline=["10.1 Future Scope"]
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
                "total_revisions": 0
            }
        }
        
        return initial_state
