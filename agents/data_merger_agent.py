# agents/data_merger_agent.py
import logging
from typing import Dict, List
import copy

from utils.id_normalization import build_canonical_id

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
            # Enforce canonical_id generation
            cid = paper.get("canonical_id")
            if not cid:
                cid = build_canonical_id(
                    primary_id=paper.get("id") or paper.get("paper_id"),
                    title=paper.get("title"),
                    source=paper.get("source")
                )
                paper["canonical_id"] = cid

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
            existing_title = existing.get("title", "Unknown")
            
            logger.debug(f"🔗 DataMerger → Merging duplicate: '{existing_title}' (Source: {paper.get('source')})")

            # Merge sources
            new_src = paper.get("source")
            if new_src:
                existing["sources"] = sorted(
                    list(set(existing.get("sources", []) + [new_src]))
                )

            # Prefer longer / more detailed title
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

            # Explicitly merge lists in metadata that deep_merge ignores (like references and concepts)
            for list_key in ["references", "concepts"]:
                existing_list = existing.get("metadata", {}).get(list_key) or []
                new_list = paper.get("metadata", {}).get(list_key) or []
                if new_list:
                    if not existing_list:
                        existing["metadata"][list_key] = new_list
                    else:
                        if isinstance(new_list[0], dict):
                            # Merge dicts by paperId (e.g. references)
                            existing_ids = {r.get("paperId") for r in existing_list if isinstance(r, dict) and r.get("paperId")}
                            added_count = 0
                            for r in new_list:
                                if isinstance(r, dict) and r.get("paperId") not in existing_ids:
                                    existing_list.append(r)
                                    existing_ids.add(r.get("paperId"))
                                    added_count += 1
                            if added_count > 0:
                                logger.debug(f"➕ Added {added_count} new {list_key} to '{existing_title}'")
                            existing["metadata"][list_key] = existing_list
                        else:
                            # Merge strings/primitives (e.g. concepts)
                            merged_set = set(existing_list + new_list)
                            if len(merged_set) > len(existing_list):
                                logger.debug(f"➕ Expanded {list_key} for '{existing_title}' to {len(merged_set)} items")
                            existing["metadata"][list_key] = list(merged_set)

            # Prefer published date if missing
            if not existing.get("published") and paper.get("published"):
                existing["published"] = paper["published"]

        merged = list(index.values())
        logger.info(f"🔗 DataMerger merged {len(papers)} → {len(merged)} unique papers")

        return merged


data_merger_agent = DataMergerAgent()
