# File: state/state_schema.py
from typing import TypedDict, List, Optional, Dict, Any

class VRAState(TypedDict, total=False):
    query: str
    user_id: str
    audience: str



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

    # Report
    draft_report: Optional[str]

    # HITL
    current_step: str
    user_feedback: Optional[str]

    # Phase 4 additions
    hypotheses: List[Dict[str, Any]]
    reviews: List[Dict[str, Any]]

    # Error handling
    error: Optional[str]
