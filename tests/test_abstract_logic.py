import pytest
from services.reporting.section_compiler import SectionCompiler

def test_abstract_compilation_with_skipped_sections():
    # Mock state where some sections (e.g. chapter_2) are not accepted,
    # but the abstract doesn't depend on them.
    # Abstract requires: "chapter_1", "chapter_4", "chapter_6", "chapter_8", "chapter_9"
    # Actually, SectionCompiler._compile_abstract doesn't throw the ValueError anymore. 
    # Let's verify it gets past the guard and hits the "generating" status.
    
    mock_state = {
        "sections": [
            {"section_id": "chapter_1", "status": "accepted", "content": "Intro"},
            {"section_id": "chapter_2", "status": "planned", "content": None}, # UNACCEPTED SECTION
            {"section_id": "chapter_4", "status": "accepted", "content": "Method"},
            {"section_id": "chapter_6", "status": "accepted", "content": "Implementation"},
            {"section_id": "chapter_8", "status": "accepted", "content": "Results"},
            {"section_id": "chapter_9", "status": "accepted", "content": "Conclusion"},
        ],
        "research_gaps": []
    }
    
    compiler = SectionCompiler(mock_state)
    target_section = {"section_id": "abstract", "status": "planned"}
    
    # We expect this to try to call _build_abstract_inputs and then generate_with_fallback.
    # We will mock _generate_with_fallback to avoid actual LLM calls during tests.
    
    import unittest.mock as mock
    
    with mock.patch.object(compiler, "_generate_with_fallback", return_value="Mocked Abstract"):
        result = compiler._compile_abstract(target_section)
        
    assert result == "Mocked Abstract"
    assert target_section["status"] == "generating" or target_section["compilation_phase"] == "COMPLETE"
