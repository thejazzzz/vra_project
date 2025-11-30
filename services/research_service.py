import asyncio
from typing import Dict
from clients.chroma_client import get_client


async def process_research_task(query: str) -> Dict:

    client = get_client()  # <-- Version A client
    doc_id = f"q-{hash(query) % 10_000}"
    loop = asyncio.get_running_loop()

    # Store text
    await loop.run_in_executor(None, client.store, doc_id, query)

    # Search back
    results = await loop.run_in_executor(None, client.search, query)

    return {
        "query": query,
        "doc_id": doc_id,
        "chroma_results": results,
    }
