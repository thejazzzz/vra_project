# tests/test_concept_filter.py
import pytest
from services.concept_filter import ConceptFilterService

def test_normalization():
    assert ConceptFilterService.normalize_concept("Fake-News Detection") == "fake news detection"
    assert ConceptFilterService.normalize_concept("  Deep_Learning  ") == "deep learning"
    assert ConceptFilterService.normalize_concept("Large Language Models") == "large language models"

def test_generic_terms_rejected():
    generic_terms = [
        "future research", "future directions", "future work",
        "insights", "analysis", "results", "discussion",
        "conclusion", "dataset creation", "methodology"
    ]
    for term in generic_terms:
        print(f"Testing term: {term}")
        assert ConceptFilterService.is_valid_concept(term) is False

def test_single_word_meta_terms_rejected():
    meta_words = ["model", "system", "approach", "framework", "algorithm"]
    for word in meta_words:
        assert ConceptFilterService.is_valid_concept(word) is False

def test_technical_single_words_accepted():
    # Technical acronyms or names should be allowed even if single words
    tech_words = ["bert", "gpt", "transformer", "gan", "lstm"]
    for word in tech_words:
        assert ConceptFilterService.is_valid_concept(word) is True

def test_compound_technical_concepts_accepted():
    valid_concepts = [
        "fake news detection",
        "multimodal deep learning",
        "graph neural networks",
        "zero-shot classification",
        "explainable ai"
    ]
    for concept in valid_concepts:
        assert ConceptFilterService.is_valid_concept(concept) is True

def test_numeric_concepts_rejected():
    assert ConceptFilterService.is_valid_concept("12345") is False
    assert ConceptFilterService.is_valid_concept("2024") is False

def test_filter_concepts_deduplication_and_fallback():
    raw = ["future research", "Future Research", "results", "Fake News Detection"]
    filtered = ConceptFilterService.filter_concepts(raw)
    
    # "future research" and "results" should be removed
    # "Fake News Detection" should be kept and normalized
    assert len(filtered) == 1
    assert filtered[0] == "fake news detection"

    # Fallback Test: If ALL are generic, keep normalized originals
    only_generic = ["future research", "insights", "Analysis"]
    fallback = ConceptFilterService.filter_concepts(only_generic)
    assert len(fallback) == 3
    assert "future research" in fallback
    assert "insights" in fallback
    assert "analysis" in fallback
