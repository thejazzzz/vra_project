# File: api/models/analysis_models.py
from pydantic import BaseModel
from typing import List, Dict, Optional


class Relation(BaseModel):
    source: str
    target: str
    relation: str


class AnalysisRequest(BaseModel):
    query: str
    # Optional: pass in papers from research step
    # Each paper dict is expected to have at least: id, title, summary
    papers: Optional[List[Dict]] = None


class AnalysisResult(BaseModel):
    summary: str
    key_concepts: List[str]
    relations: List[Relation]


class AnalysisResponse(BaseModel):
    status: str
    data: AnalysisResult
