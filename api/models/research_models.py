# File: api/models/research_models.py
from pydantic import BaseModel
from typing import Any, Dict, Literal

class ResearchRequest(BaseModel):
    query: str
    audience: Literal["general", "phd", "industry"] = "general"


class ResearchResponse(BaseModel):
    status: str
    data: Dict[str, Any]