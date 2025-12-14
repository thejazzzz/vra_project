# agents/arxiv_agent.py
import asyncio
import logging
from typing import List, Dict

from clients.arxiv_client import search_arxiv
from utils.sanitization import clean_text, is_nonempty_text
from utils.id_normalization import normalize_arxiv_id, to_canonical_id

logger = logging.getLogger(__name__)


class ArxivAgent:
    async def run(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Fetch papers from arXiv and normalize them.
        """
        logger.info(f"📡 arXiv Agent: searching for '{query}'")

        try:
            raw_results = await asyncio.to_thread(search_arxiv, query, limit)
        except Exception as e:
            logger.error(f"Failed to search arXiv: {e}")
            return []
        normalized = []
        for p in raw_results:
            raw_id = p.get("id")
            arxiv_id = normalize_arxiv_id(raw_id)

            if not arxiv_id:
                continue

            title = clean_text(p.get("title"))
            abstract = clean_text(p.get("summary"))

            if not (is_nonempty_text(title) or is_nonempty_text(abstract)):
                continue

            canonical_id = to_canonical_id("arxiv", arxiv_id)

            normalized.append({
                "canonical_id": canonical_id,
                "paper_id": arxiv_id,
                "source": "arxiv",
                "sources": ["arxiv"],

                "title": title,
                "summary": abstract,
                "pdf_url": p.get("pdf_url"),

                "authors": p.get("authors", []),
                "published": p.get("published"),
                "metadata": p,
            })

        logger.info(f"📚 arXiv Agent returned {len(normalized)} papers")
        return normalized


arxiv_agent = ArxivAgent()
