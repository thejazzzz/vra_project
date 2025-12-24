# File: api/models/research_models.py
from pydantic import BaseModel
from typing import Any, Dict, Literal

class ResearchRequest(BaseModel):
    query: str
    audience: Literal["general", "phd", "industry"] = "general"


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