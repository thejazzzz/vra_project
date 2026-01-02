# File: state/state_schema.py
from typing import TypedDict, List, Optional, Dict, Any, Literal

# Phase 3.2: Interactive Reporting Types
class SectionHistory(TypedDict):
    revision: int
    content: str       # Markdown
    content_hash: str  # SHA256 integrity check
    feedback: Optional[str]
    timestamp: str
    prompt_version: str # e.g. "v1.2"
    model_name: str     # e.g. "gpt-4o"

class ReportSectionState(TypedDict):
    section_id: str
    status: Literal["planned", "generating", "review", "accepted", "error"]
    title: str
    description: str
    depends_on: List[str] # IDs of sections that must be ACCEPTED before this one starts
    template_key: str     # Key for prompt template
    
    content: Optional[str] # Current active content
    revision: int          # Current revision number
    max_revisions: int     # Default: 3
    history: List[SectionHistory]
    quality_scores: Optional[Dict[str, float]] # e.g. {"coherence": 0.9}

class ReportState(TypedDict):
    # Global Lifecycle
    report_status: Literal["idle", "planned", "in_progress", "awaiting_final_review", "validating", "finalizing", "exporting", "completed", "failed"]
    sections: List[ReportSectionState]
    
    # Concurrency & Integrity
    locks: Dict[str, Any] # {"report": bool, "sections": Dict[str, bool]}
    last_successful_step: Optional[Dict[str, str]] # {"section_id": "...", "phase": "..."}
    section_order_hash: str # SHA256 of planner output
    
    # User Intent Guards
    user_confirmed_start: bool
    user_confirmed_finalize: bool
    
    # Metadata
    created_at: str
    updated_at: str
    metrics: Dict[str, Any] # { "avg_revisions": 1.2, "generation_time_ms": ... }

class VRAState(TypedDict, total=False):
    query: str
    user_id: str
    audience: Literal["phd", "rd", "industry", "general"]



    # Paper data
    collected_papers: List[Dict[str, Any]]
    selected_papers: List[Dict[str, Any]]
    added_papers: List[Dict[str, Any]]

    # Phase 3 additions
    paper_structured_summaries: Dict[str, Dict[str, str]]
    research_gaps: List[Dict[str, Any]]
    author_graph: Dict[str, Any]
    concept_trends: Dict[str, Any]
    
    # Safety & Versioning (Phase 3.1)
    graph_approved: bool
    workflow_version: str

    # Per-paper analysis
    paper_summaries: Dict[str, str]        # {paper_id: summary}
    paper_concepts: Dict[str, List[str]]   # {paper_id: [concepts]}
    paper_relations: Dict[str, List[Dict[str, Any]]] # {paper_id: [{relation}]}

    # Global analysis (current implementation)
    global_analysis: Dict[str, Any]

    # Global structures
    knowledge_graph: Dict[str, Any]
    citation_graph: Dict[str, Any]

    # Report (Phase 3.2 Enhanced)
    draft_report: Optional[str] # Deprecated but kept for backward compatibility
    report_state: ReportState   # New structured state

    # HITL
    current_step: str
    user_feedback: Optional[str]

    # Phase 4 additions
    hypotheses: List[Dict[str, Any]]
    reviews: List[Dict[str, Any]]

    # Error handling
    error: Optional[str]
