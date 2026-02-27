import asyncio
import traceback
from services.trend_analysis_service import detect_concept_trends

papers = [
    {"canonical_id": "p1", "year": "2020", "citationCount": "10"},
    {"canonical_id": "p2", "year": "2021", "citationCount": "5"},
    {"canonical_id": "p3", "year": "2022", "citationCount": None},
    {"canonical_id": "p4", "year": "2022"}
]
concepts_per_paper = {
    "p1": ["AI", "ML", None], 
    "p2": ["ML", "Data"],
    "p3": None,
    "p4": ["AI", "AI"]
}
paper_relations = {}

try:
    print("Running detect_concept_trends...")
    result = detect_concept_trends(papers, concepts_per_paper, paper_relations, use_citation_weighting=True)
    print("Success:", result)
except Exception as e:
    print("FAILED!")
    traceback.print_exc()
