# File: agents/semantic_scholar_agent.py
import logging
from typing import List, Dict
from clients.semantic_scholar_client import search_semantic_scholar
from utils.sanitization import clean_text, is_nonempty_text
import asyncio

logger = logging.getLogger(__name__)


class SemanticScholarAgent:
    async def run(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Fetch papers from Semantic Scholar and normalize them.
        Will be used in multi-source acquisition.
        """
        logger.info(f"🔎 Semantic Scholar Agent: searching for '{query}'")

        results = await asyncio.to_thread(search_semantic_scholar, query, limit)

        cleaned_results = []
        for p in results:
            title = clean_text(p.get("title"))
            abstract = clean_text(p.get("abstract"))

            if not (is_nonempty_text(title) or is_nonempty_text(abstract)):
                continue

            cleaned_results.append({
                "id": p.get("paper_id"),      # unified naming
                "title": title,
                "summary": abstract,
                "source": "semantic_scholar",
                "pdf_url": p.get("pdf_url"),
                "authors": p.get("authors", []),
                "published": p.get("published"),
                "metadata": p.get("metadata", {}),
            })
        logger.info(f"📚 Semantic Scholar returned {len(cleaned_results)} papers")

        return cleaned_results


semantic_scholar_agent = SemanticScholarAgent()
