# api/models/analysis_models.py
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Literal


class GraphEditRequest(BaseModel):
    action: Literal["add_node", "remove_node", "add_edge", "remove_edge", "update_edge", "update_node"]
    node_id: Optional[str] = None
    node_label: Optional[str] = None
    node_type: Optional[str] = "concept"
    source: Optional[str] = None
    target: Optional[str] = None
    relation: Optional[str] = None
    updates: Optional[dict] = None

    @model_validator(mode="after")
    def validate_action_fields(self):
        action = self.action
        if action in ["add_node", "update_node", "remove_node"]:
            if not self.node_id:
                raise ValueError(f"action '{action}' requires 'node_id' to be provided.")
        if action in ["add_edge", "remove_edge", "update_edge"]:
            if not self.source or not self.target:
                raise ValueError(f"action '{action}' requires 'source' and 'target' to be provided.")
        if action.startswith("update_"):
            if not self.updates:
                raise ValueError(f"action '{action}' requires 'updates' to be present and non-empty.")
        return self

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
