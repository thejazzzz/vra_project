# File: api/models/research_models.py
from pydantic import BaseModel, Field
from typing import Any, Dict, Literal, List, Optional

class ResearchRequest(BaseModel):
    query: str
    audience: Literal["general", "phd", "industry", "rd"] = "general"
    include_paper_ids: list[str] = Field(default_factory=list)
    task_id: Optional[str] = None


class ResearchResponse(BaseModel):
    status: str
    data: Dict[str, Any]

class ManualPaperRequest(BaseModel):
    query: str
    title: str
    abstract: str
    url: str = ""
    authors: list[str] = []
    year: int = 2024
    source: str = "user_upload"