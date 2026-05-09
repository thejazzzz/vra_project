
import asyncio
import logging
import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from agents.data_acquisition_agent import data_acquisition_agent

async def test():
    logging.basicConfig(level=logging.INFO)
    query = "transformer neural networks"
    print(f"Testing DataAcquisitionAgent with query: {query}")
    papers = await data_acquisition_agent.run(query, limit=5)
    print(f"Total papers returned: {len(papers)}")
    for i, p in enumerate(papers):
        title = p.get("title")
        meta = p.get("metadata", {})
        ref_count = meta.get("referenceCount") or p.get("reference_count") or 0
        cit_count = meta.get("citationCount") or p.get("citation_count") or 0
        has_refs = "Yes" if meta.get("references") else "No"
        print(f"{i+1}. {title} | Refs: {ref_count} | Citations: {cit_count} | Has References Data: {has_refs}")

if __name__ == "__main__":
    asyncio.run(test())
