# File: api/models/analysis_models.py
from pydantic import BaseModel, Field
from typing import List, Optional


class Paper(BaseModel):
    id: str = Field(..., description="Unique identifier e.g., arXiv URL")
    title: str = Field(..., description="Title of the paper")
    summary: str = Field(..., description="Abstract or summary of the paper")


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
