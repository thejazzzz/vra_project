# agents/semantic_scholar_agent.py
import asyncio
import logging
from typing import List, Dict

from clients.semantic_scholar_client import search_semantic_scholar, get_papers_by_ids
from utils.sanitization import clean_text, is_nonempty_text
from utils.id_normalization import to_canonical_id

logger = logging.getLogger(__name__)


class SemanticScholarAgent:
    async def run(self, query: str, limit: int = 5) -> List[Dict]:
        logger.info(f"🔎 Semantic Scholar Agent: searching for '{query}'")

        results = await asyncio.to_thread(search_semantic_scholar, query, limit)
        normalized = []

        for p in results:
            # Proper Semantic Scholar identifier
            s2_id = p.get("paper_id") or p.get("paperId")
            if not s2_id:
                continue

            title = clean_text(p.get("title"))
            abstract = clean_text(p.get("abstract"))

            if not (is_nonempty_text(title) or is_nonempty_text(abstract)):
                continue

            canonical_id = to_canonical_id("semantic_scholar", s2_id)

            normalized.append({
                "canonical_id": canonical_id,
                "paper_id": s2_id,
                "source": "semantic_scholar",
                "sources": ["semantic_scholar"],

                "title": title,
                "summary": abstract,
                "pdf_url": p.get("pdf_url"),

                "authors": p.get("authors", []),
                "published": p.get("published"),
                "metadata": p,   # keep entire S2 metadata structure
            })

        logger.info(f"📘 Semantic Scholar Agent returned {len(normalized)} papers")
        return normalized

    async def get_by_ids(self, paper_ids: List[str]) -> List[Dict]:
        logger.info(f"🔎 Semantic Scholar Agent: fetching {len(paper_ids)} specific IDs")
        results = await asyncio.to_thread(get_papers_by_ids, paper_ids)
        normalized = []

        for p in results:
            s2_id = p.get("paper_id") or p.get("paperId")
            if not s2_id: continue

            title = clean_text(p.get("title"))
            abstract = clean_text(p.get("abstract"))
            if not (is_nonempty_text(title) or is_nonempty_text(abstract)): continue

            canonical_id = to_canonical_id("semantic_scholar", s2_id)
            p_dict = p.copy()
            p_dict.update({
                "canonical_id": canonical_id,
                "sources": ["semantic_scholar"]
            })
            # Ensure summary maps to abstract for uniform interface
            p_dict["summary"] = abstract 
            normalized.append(p_dict)
            
        logger.info(f"📘 Semantic Scholar Agent retrieved {len(normalized)} specific link papers")
        return normalized


semantic_scholar_agent = SemanticScholarAgent()
