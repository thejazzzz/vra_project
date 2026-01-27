# services/formatter/schema.py
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

class FormattedTable(BaseModel):
    # TODO: Fully implement Table support in Normalizer and Renderers
    id: str
    caption: str
    content: str 
    index: int 

class FormattedFigure(BaseModel):
    # TODO: Fully implement Figure support in Normalizer and Renderers
    id: str
    caption: str
    path: Optional[str] = None
    content: Optional[str] = None 
    index: int

class FormattedSection(BaseModel):
    id: str
    title: str
    level: int # 1, 2, 3
    numbering: str # "1", "1.1", "1.2.1"
    content: str # Markdown content of the section body
    subsections: List['FormattedSection'] = Field(default_factory=list)

class FormattedReference(BaseModel):
    id: str
    text: str
    url: Optional[str] = None
    index: int # [1], [2]

class FormattedReport(BaseModel):
    title: str
    subtitle: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    date: str
    abstract: Optional[str] = None
    
    sections: List[FormattedSection] = Field(default_factory=list)
    references: List[FormattedReference] = Field(default_factory=list)
    
    # Metadata
    meta: Dict[str, Any] = Field(default_factory=dict)

# Fix recursive reference
FormattedSection.update_forward_refs()
