# services/concept_filter.py
"""
Semantic Concept Filtering Service for VRA Research Gap Detection.

Prevents generic meta-terms (e.g. "future research", "insights", "analysis")
from entering the knowledge graph and polluting gap analysis results.

Design principle: CONSERVATIVE. When in doubt, KEEP the concept.
The stop-list is intentionally narrow to ensure real research results
are never suppressed.
"""

import re
import logging
from typing import List

logger = logging.getLogger(__name__)


class ConceptFilterService:
    """
    Filters and normalizes research concepts extracted from papers.
    Used as a pre-processing step before graph ingestion and gap detection.
    """

    # ----------------------------------------------------------------
    # Stop-concept list: ONLY clear structural/meta paper terms.
    # Do NOT add domain words (e.g."detection", "model") as single
    # words because they may form valid compound concepts.
    # ----------------------------------------------------------------
    GENERIC_STOP_CONCEPTS = frozenset([
        # Paper structure headers
        "future research",
        "future work",
        "future direction",
        "future directions",
        "related work",
        "related works",
        # Generic descriptors used as standalone "concepts"
        "insights",
        "insight",
        "findings",
        "finding",
        "results",
        "result",
        "discussion",
        "conclusion",
        "conclusions",
        "introduction",
        "background",
        "overview",
        "summary",
        "abstract",
        # Research process meta-terms
        "dataset creation",
        "data collection",
        "data collection process",
        "analysis",
        "methodology",
        "methods",
        "approach",
        "framework",
        "study",
        "research",
        "paper",
        "experiment",
        "experiments",
        "evaluation",
        "performance",
        "implementation",
        "proposal",
        "contribution",
        "contributions",
        "limitation",
        "limitations",
    ])

    # Single-word terms that are too generic on their own but valid
    # when part of compound concepts. Used in is_valid_concept() to
    # reject these as standalone single-word concepts.
    _SINGLE_WORD_META_TERMS = frozenset([
        "model", "system", "method", "technique", "approach",
        "framework", "algorithm", "tool", "platform",
    ])

    @classmethod
    def normalize_concept(cls, concept: str) -> str:
        """
        Normalize a concept string for comparison and graph ingestion.
        - Lowercases
        - Replaces hyphens and underscores with spaces
        - Collapses multiple whitespace into one
        - Strips leading/trailing whitespace
        """
        if not concept or not isinstance(concept, str):
            return ""
        concept = concept.lower()
        concept = concept.replace("-", " ").replace("_", " ")
        concept = re.sub(r"\s+", " ", concept)
        return concept.strip()

    @classmethod
    def is_valid_concept(cls, concept: str) -> bool:
        """
        Returns True if the concept is a meaningful domain-specific term.
        Returns False for generic meta-terms, single meta-words, or empty strings.
        Single-word technical terms (e.g., "bert", "transformer") are allowed.

        Conservative approach: only rejects clearly invalid concepts.
        """
        if not concept or not isinstance(concept, str):
            return False

        normalized = cls.normalize_concept(concept)

        if not normalized:
            return False

        # Rule 1: Block-list check
        if normalized in cls.GENERIC_STOP_CONCEPTS:
            logger.debug(f"ConceptFilter: blocked generic concept '{normalized}'")
            return False

        # Rule 2: Purely numeric strings have no conceptual value
        if normalized.replace(" ", "").isdigit():
            return False

        # Rule 3: Single-word concepts are almost always too vague.
        # Exception: allow if the word itself is highly technical
        # (i.e. not in the single-word meta-terms set).
        word_count = len(normalized.split())
        if word_count < 2:
            # Allow single technical words that are NOT meta-terms
            if normalized in cls._SINGLE_WORD_META_TERMS:
                logger.debug(f"ConceptFilter: blocked single meta-word '{normalized}'")
                return False
            # Single-word concepts that are NOT in the meta list are allowed
            # (e.g. "bert", "gpt", "transformer" are valid single-word concepts)
            return True

        # All other concepts are accepted
        return True

    @classmethod
    def filter_concepts(cls, concepts: List[str]) -> List[str]:
        """
        Normalize, filter, and deduplicate a list of concept strings.

        Returns a cleaned list. If filtering removes ALL concepts,
        returns the original list (normalized) to avoid empty outputs.
        This ensures the system always produces results.
        """
        if not concepts:
            return []

        seen = set()
        filtered = []

        for raw in concepts:
            normalized = cls.normalize_concept(raw)
            if not normalized:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            if cls.is_valid_concept(normalized):
                filtered.append(normalized)

        # Safety fallback: if the filter removed everything (e.g. a paper
        # with an entirely generic concept list from the LLM), keep the
        # normalized originals so we don't starve the graph of data.
        if not filtered and concepts:
            logger.warning(
                "ConceptFilter: all %d concepts were filtered out — "
                "falling back to normalized originals to avoid empty graph.",
                len(concepts)
            )
            # Return deduplicated normalized originals, skipping empty strings
            fallback_seen = set()
            fallback = []
            for raw in concepts:
                norm = cls.normalize_concept(raw)
                if norm and norm not in fallback_seen:
                    fallback_seen.add(norm)
                    fallback.append(norm)
            return fallback

        logger.debug(
            "ConceptFilter: %d/%d concepts passed filtering.",
            len(filtered), len(concepts)
        )
        return filtered
