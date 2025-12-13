# models/paper_normalized.py
from typing import Dict, List, Optional, TypedDict


class NormalizedPaper(TypedDict, total=False):
    """
    Unified normalized structure for all papers before DB insertion.
    """

    canonical_id: str        # e.g., 'arxiv:2306.11113v2'
    paper_id: str            # old system field (arxiv or s2 ID, etc.)
    source: str              # primary source for acquisition

    title: str
    summary: str
    pdf_url: Optional[str]
    authors: List[str]
    published: Optional[str]

    sources: List[str]       # all sources contributing to this record

    metadata: Dict           # full raw metadata from provider
