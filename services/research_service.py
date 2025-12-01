# File: services/research_service.py
import asyncio
import logging
from typing import Dict
from clients.arxiv_client import search_arxiv
from clients.chroma_client import get_client

logger = logging.getLogger(__name__)

async def process_research_task(query: str) -> Dict:
    client = get_client()

    try:
        papers = await asyncio.to_thread(search_arxiv, query)
    except Exception as e:
        logger.error(f"ArXiv search failed: {e}", exc_info=True)
        papers = []

    if not isinstance(papers, list):
        logger.error(f"ArXiv returned type {type(papers).__name__}, expected list")
        papers = []
    elif len(papers) == 0:
        logger.warning(f"No papers found for query: {query}")
    else:
        logger.info(f"Fetched {len(papers)} papers for query: {query}")

    # Map each storage task to the correct paper
    storage_tasks = []
    task_to_paper = {}  # task_idx -> (paper_idx, paper_id)

    for idx, paper in enumerate(papers):
        paper_id = paper.get("id")
        summary = paper.get("summary")

        if not (paper_id and summary):
            logger.warning(f"Skipping incomplete paper at index {idx}")
            continue

        doc_id = f"{paper_id}-{idx}"
        task_idx = len(storage_tasks)
        
        storage_tasks.append(asyncio.to_thread(client.store, doc_id, summary, paper))
        task_to_paper[task_idx] = (idx, paper_id)

    failed_papers = []

    if storage_tasks:
        results = await asyncio.gather(*storage_tasks, return_exceptions=True)
        
        for task_idx, r in enumerate(results):
            if isinstance(r, Exception):
                paper_idx, paper_id = task_to_paper[task_idx]
                failed_papers.append({
                    "paper_id": paper_id,
                    "error": str(r)
                })

        if failed_papers:
            failed_ids = [fp["paper_id"] for fp in failed_papers]
            logger.error(f"Failed to store {len(failed_papers)} papers: {failed_ids}")

    return {
        "query": query,
        "papers_found": len(papers),
        "storage_failed": len(failed_papers),
        "failed_paper_ids": [fp["paper_id"] for fp in failed_papers],
        "papers": papers
    }
