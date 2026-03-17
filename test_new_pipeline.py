# File: test_new_pipeline.py
import asyncio
import logging
from pprint import pprint

from services.llm.orchestrator import LLMOrchestrator
from services.reporting.outline_generator import OutlineGenerator
from services.reporting.anchor_generator import AnchorGenerator
from services.reporting.independent_generator import IndependentGenerator
from services.reporting.global_polisher import GlobalPolisher

logging.basicConfig(level=logging.INFO)

def run_tests():
    print("=== Testing LLMOrchestrator ===")
    try:
        response = LLMOrchestrator.robust_generate_response("Hello, are you there?", temperature=0.1)
        print(f"Orchestrator Response: {response[:100]}...\n")
    except Exception as e:
        print(f"Orchestrator failed: {e}")

    mock_state = {
        "query": "The impact of artificial intelligence on healthcare",
        "report_type": "Short Overview",
        "target_length_words": 1000,
        "audience": "General Public",
        "selected_papers": [
            {
                "paper_id": "1",
                "title": "AI in Medical Diagnostics",
                "abstract": "This paper discusses how AI models can detect diseases from medical images with high accuracy."
            },
            {
                "paper_id": "2",
                "title": "Ethics of AI Healthcare",
                "abstract": "We explore the ethical implications of using AI in patient care, focusing on data privacy."
            }
        ]
    }

    print("=== Testing OutlineGenerator ===")
    try:
        outline = OutlineGenerator.generate_outline(mock_state)
        print("Generated Outline:")
        pprint(outline)
        print()
    except Exception as e:
        print(f"OutlineGenerator failed: {e}")
        return

    if not outline:
        print("Outline generation returned empty.")
        return

    first_section = outline[0]
    
    print("=== Testing AnchorGenerator ===")
    try:
        anchors = AnchorGenerator.generate_anchors(
            section_title=first_section["title"],
            section_description=first_section["description"],
            state=mock_state
        )
        print(f"Generated Anchors for '{first_section['title']}':")
        print(anchors)
        print()
    except Exception as e:
        print(f"AnchorGenerator failed: {e}")
        return

    print("=== Testing IndependentGenerator ===")
    try:
        section_content = IndependentGenerator.generate_section(
            topic=mock_state["query"],
            section_title=first_section["title"],
            section_description=first_section["description"],
            anchors=anchors,
            target_words=first_section["target_words"]
        )
        print(f"Generated Content for '{first_section['title']}':")
        print(section_content[:500] + "...\n")
    except Exception as e:
        print(f"IndependentGenerator failed: {e}")
        return
        
    print("=== Testing IndependentGenerator (Smart Expand) ===")
    try:
        # Pass a very short string to force expansion
        expanded_content = IndependentGenerator.expand_section_if_needed("This section is too short. It only has a few words.", 100)
        print(f"Expanded Content:")
        print(expanded_content)
        print()
    except Exception as e:
        print(f"Smart Expand failed: {e}")
        return
        
    print("=== Testing GlobalPolisher ===")
    try:
        test_report = f"## {first_section['title']}\n{section_content}\n\n## Ethical Concerns\nAnother important aspect is ethics."
        polished = GlobalPolisher.run_consistency_pass(test_report)
        print(f"Polished Report:")
        print(polished[:500] + "...\n")
        print()
    except Exception as e:
        print(f"GlobalPolisher failed: {e}")
        return

    print("All tests completed.")

if __name__ == "__main__":
    run_tests()
