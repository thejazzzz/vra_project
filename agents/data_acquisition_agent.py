# agents/data_acquisition_agent.py
import logging
from typing import List, Dict
import asyncio

from agents.arxiv_agent import arxiv_agent
from agents.semantic_scholar_agent import semantic_scholar_agent
from agents.data_merger_agent import data_merger_agent

logger = logging.getLogger(__name__)


class DataAcquisitionAgent:
    async def run(self, query: str, limit: int = 5) -> List[Dict]:
        """
        High-level entry point for acquiring research papers from all sources.
        """

        logger.info(f"🌐 DataAcquisitionAgent → starting for '{query}'")

        # Call all sources concurrently
        arxiv, s2 = await asyncio.gather(
            arxiv_agent.run(query, limit),
            semantic_scholar_agent.run(query, limit)
        )

        combined = arxiv + s2

        logger.info(f"📥 Total papers fetched (before merge): {len(combined)}")

        # Deduplicate + merge metadata
        merged = data_merger_agent.merge(combined)

        logger.info(f"📦 Final merged paper count: {len(merged)}")
        return merged


data_acquisition_agent = DataAcquisitionAgent()
