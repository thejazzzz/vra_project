# agents/data_merger_agent.py
import logging
from typing import Dict, List
import copy

logger = logging.getLogger(__name__)


def deep_merge(base: dict, updates: dict) -> dict:
    """Deep merge dictionaries, preferring existing values."""
    result = base.copy()
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        elif key not in result:
            result[key] = value
    return result


class DataMergerAgent:
    """
    Deduplicates and merges papers across all acquisition agents.
    Uses canonical_id as the unique identifier.
    """

    def merge(self, papers: List[Dict]) -> List[Dict]:
        index: Dict[str, Dict] = {}

        for paper in papers:
            cid = paper.get("canonical_id")
            if not cid:
                logger.warning(f"Skipping paper without canonical_id: {paper.get('title', 'Unknown')}")
                continue

            # ----------------------------
            # First occurrence = store
            # ----------------------------
            if cid not in index:
                obj = copy.deepcopy(paper)

                src = paper.get("source")
                obj["sources"] = [src] if src else []

                index[cid] = obj
                continue

            # ----------------------------
            # Merge duplicate
            # ----------------------------
            existing = index[cid]

            # Merge sources
            new_src = paper.get("source")
            if new_src:
                existing["sources"] = sorted(
                    list(set(existing.get("sources", []) + [new_src]))
                )

            # Prefer longer / more detailed title
            existing_title = existing.get("title") or ""
            paper_title = paper.get("title") or ""
            if len(paper_title) > len(existing_title):
                existing["title"] = paper_title

            # Prefer more detailed abstract
            existing_summary = existing.get("summary") or ""
            paper_summary = paper.get("summary") or ""
            if len(paper_summary) > len(existing_summary):
                existing["summary"] = paper_summary

            # Merge authors (only if missing)
            if not existing.get("authors"):
                existing["authors"] = paper.get("authors", [])

            # Deep merge metadata
            existing["metadata"] = deep_merge(
                existing.get("metadata", {}),
                paper.get("metadata", {})
            )

            # Prefer published date if missing
            if not existing.get("published") and paper.get("published"):
                existing["published"] = paper["published"]

        merged = list(index.values())
        logger.info(f"🔗 DataMerger merged {len(papers)} → {len(merged)} unique papers")

        return merged


data_merger_agent = DataMergerAgent()
