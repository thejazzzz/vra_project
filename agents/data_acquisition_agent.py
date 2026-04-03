# agents/data_acquisition_agent.py
import logging
from typing import List, Dict
import asyncio

from agents.arxiv_agent import arxiv_agent
from agents.semantic_scholar_agent import semantic_scholar_agent
from agents.data_merger_agent import data_merger_agent

logger = logging.getLogger(__name__)


class DataAcquisitionAgent:
    async def run(self, query: str, limit: int = 5, expand_citations: bool = True) -> List[Dict]:
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

        if expand_citations and merged:
            logger.info("❄️ Snowballing: Expanding citation network from top papers...")
            # Sort by citation count
            top_papers = sorted(
                merged, 
                key=lambda x: (x.get("metadata") or {}).get("citationCount") or x.get("citation_count") or 0, 
                reverse=True
            )[:3] # Top 3 highly cited papers
            
            ref_ids = set()
            for p in top_papers:
                refs = (p.get("metadata") or {}).get("references") or p.get("references") or []
                for r in refs:
                    rid = r.get("paperId")
                    if rid: ref_ids.add(rid)
                    
            # Filter already fetched
            existing_s2_ids = {p.get("paper_id") for p in merged if p.get("source") == "semantic_scholar"}
            ref_ids = list(ref_ids - existing_s2_ids)
            
            # Fetch in batches if necessary, take top 10 to avoid massive pulls and rate limit issues
            ref_ids = ref_ids[:10]
            if ref_ids:
                extra_papers = await semantic_scholar_agent.get_by_ids(ref_ids)
                if extra_papers:
                    logger.info(f"❄️ Snowballing retrieved {len(extra_papers)} additional linked papers.")
                    merged = data_merger_agent.merge(merged + extra_papers)

        logger.info(f"📦 Final merged paper count: {len(merged)}")
        return merged


data_acquisition_agent = DataAcquisitionAgent()
