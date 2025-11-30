# File: services/research_service.py
import asyncio
from typing import Dict
from clients.arxiv_client import search_arxiv
from clients.chroma_client import get_client

async def process_research_task(query: str) -> Dict:
    client = get_client()

    # Run ArXiv query in a thread
    papers = await asyncio.to_thread(search_arxiv, query)

    # Store paper abstracts concurrently
    storage_tasks = []
    for idx, paper in enumerate(papers):
        doc_id = f"{paper['id']}-{idx}"
        storage_tasks.append(
            asyncio.to_thread(client.store, doc_id, paper["summary"], paper)
        )

    if storage_tasks:
        results = await asyncio.gather(*storage_tasks, return_exceptions=True)
        failed = [i for i, r in enumerate(results) if isinstance(r, Exception)]
        if failed:
            # Log or handle failures appropriately
            pass


    return {
        "query": query,
        "papers_found": len(papers),
        "papers": papers
    }
