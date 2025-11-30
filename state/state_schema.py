# File: state/state_schema.py
from typing import TypedDict, List, Optional, Dict

class VRAState(TypedDict, total=False):
    query: str
    collected_papers: List[Dict]
    analysis_results: Dict
    draft_report: Optional[str]
    user_feedback: Optional[str]
    current_step: str

