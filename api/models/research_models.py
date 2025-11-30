# File: api/models/research_models.py
from pydantic import BaseModel
from typing import Any, Dict

class ResearchRequest(BaseModel):
    query: str

class ResearchResponse(BaseModel):
    status: str
    data: Dict[str, Any]