# File: state/state_schema.py
from typing import TypedDict, List, Optional, Dict

class VRAState(TypedDict, total=False):
    query: str

    # Paper data
    collected_papers: List[Dict]
    selected_papers: List[Dict]
    added_papers: List[Dict]

    # Per-paper analysis
    paper_summaries: Dict[str, str]        # {paper_id: summary}
    paper_concepts: Dict[str, List[str]]   # {paper_id: [concepts]}
    paper_relations: Dict[str, List[Dict]] # {paper_id: [{relation}]}

    # Global structures
    knowledge_graph: Dict
    citation_graph: Dict

    # Report
    draft_report: Optional[str]

    # HITL
    current_step: str
    user_feedback: Optional[str]

