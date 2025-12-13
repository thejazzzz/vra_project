# api/models/analysis_models.py
from pydantic import BaseModel, Field
from typing import List, Optional


class Paper(BaseModel):
    id: str = Field(..., description="Canonical paper identifier (e.g., arxiv:2306.11113)")
    title: str = Field(..., description="Cleaned title of the paper")
    summary: str = Field("", description="Abstract or summary of the paper")


class Relation(BaseModel):
    source: str
    target: str
    relation: str


class AnalysisRequest(BaseModel):
    query: str
    papers: Optional[List[Paper]] = None


class AnalysisResult(BaseModel):
    summary: str
    key_concepts: List[str]
    relations: List[Relation]


class AnalysisResponse(BaseModel):
    status: str
    data: AnalysisResult
