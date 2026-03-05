import asyncio
import os
import sys
import json
import logging

logging.basicConfig(level=logging.INFO)

# Set dummy env vars to bypass database initializations
os.environ["SUPABASE_URL"] = "http://localhost:8000"
os.environ["SUPABASE_KEY"] = "mock_key"
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["OLLAMA_MODEL"] = "llama3:8b"
os.environ["POSTGRES_USER"] = "mock"
os.environ["POSTGRES_PASSWORD"] = "mock"
os.environ["POSTGRES_DB"] = "mock"

# Important: these must be set so SemanticScholar doesn't fail on import if it has global checks
from services.reporting.section_planner import SectionPlanner
from services.reporting.section_compiler import SectionCompiler
from state.state_schema import VRAState

async def test_reporting():
    print("Testing SectionCompiler and ContextBuilder directly...")
    
    # Create a mock state with rich data
    mock_state: VRAState = {
        "session_id": "test_session_123",
        "query": "Applications of Graph Neural Networks in Drug Discovery",
        "audience": "phd",
        "selected_papers": [
            {"paper_id": "p1", "title": "GNNs for Molecular Property Prediction", "abstract": "We present a novel GNN for predicting toxicity."},
            {"paper_id": "p2", "title": "Graph Representation Learning in Biology", "abstract": "A review of representation learning on graphs."}
        ],
        "paper_summaries": {
            "p1": "This paper shows GNNs are highly effective for molecular property prediction.",
            "p2": "Provides a comprehensive overview of graph representation learning in biology."
        },
        "citation_metrics": {
            "PageRank": {"p1": 0.85, "p2": 0.45},
            "citation_velocity": {"p1": 150, "p2": 40}
        },
        "global_analysis": {
            "themes": "Drug discovery, Graph architectures, Toxicity prediction"
        },
        "concept_trends": {
            "trends": {
                "Molecular Graphs": {"status": "Emerging", "growth_rate": 0.8},
                "GCNs": {"status": "Saturated", "growth_rate": 0.1}
            }
        },
        "research_gaps": [
            {"description": "Lack of interpretability in GNN models for biology.", "rationale": "Most models act as black boxes."},
            {"description": "Out-of-distribution generalization is poor.", "rationale": "Scaffolds differ heavily between training and test sets."}
        ]
    }
    
    print("\n--- Initializing Report Plan ---")
    report_state = SectionPlanner.initialize_report_state(mock_state)
    mock_state["report_state"] = report_state # Attach to state
    
    sections = report_state.get("sections", [])
    print(f"Plan initialized with {len(sections)} sections.")
    for s in sections:
        print(f" - [{s['section_id']}] {s['title']} ({s['section_type']})")

    compiler = SectionCompiler(mock_state)
    
    # NEW: Monkey patch the LLM call to print the prompt and avoid waiting for Ollama
    original_generate = compiler._generate_with_fallback
    def mock_generate(prompt: str, *args, **kwargs) -> str:
        print("\n" + "="*80)
        print("MOCKED LLM PAYLOAD INTERCEPTED:")
        print("="*80)
        # Check if system_prompt exists in kwargs
        if "system_prompt" in kwargs:
             print("[SYSTEM PROMPT]: " + kwargs["system_prompt"] + "\n")
        print(prompt)
        print("="*80 + "\n")
        return "This is a dummy generated response to bypass LLM inference time. " * 20
    
    # Needs to be bound or take exact arguments depending on python invocation, easiest is python replacing instance methods doesn't pass self
    compiler._generate_with_fallback = mock_generate

    # Let's try generating Chapter 1 (Introduction)
    chapter_1_id = "chapter_1"
    print(f"\n--- Generating {chapter_1_id} ---")
    
    c1 = next((s for s in sections if s["section_id"] == chapter_1_id), None)
    if c1:
        content_1 = compiler.compile(c1)
        print("Success! Content generated:")
        print(content_1[:500] + "...\n")
        
        # Accept Chapter 1 to put it into rolling memory
        print(f"Accepting {chapter_1_id}...")
        c1["status"] = "accepted"
        c1["content"] = content_1
    else:
        print(f"Failed to find {chapter_1_id}.")
        
    # Let's generate Chapter 4 (Knowledge Graph Analysis)
    chapter_4_id = "chapter_4"
    print(f"\n--- Generating {chapter_4_id} ---")
    
    c4 = next((s for s in sections if s["section_id"] == chapter_4_id), None)
    if c4:
        content_4 = compiler.compile(c4)
        print("Success! Content generated:")
        print(content_4[:500] + "...\n")
    else:
        print(f"Failed to find {chapter_4_id}.")

if __name__ == "__main__":
    asyncio.run(test_reporting())
