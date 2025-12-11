# File: clients/semantic_scholar_client.py
import logging
import os
import requests
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

S2_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = [
    "title",
    "abstract",
    "authors",
    "year",
    "externalIds",
    "url",
]

API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")  # optional but recommended


def search_semantic_scholar(query: str, limit: int = 5) -> List[Dict]:
    """
    Searches Semantic Scholar for papers matching the query.

    Returns a list of dicts matching the NormalizedPaper structure.
    """
    params = {
        "query": query,
        "limit": limit,
        "fields": ",".join(S2_FIELDS),
    }

    headers = {}
    if API_KEY:
        headers["x-api-key"] = API_KEY

    try:
        resp = requests.get(S2_API_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Semantic Scholar request failed: {e}", exc_info=True)
        return []

    results = data.get("data", [])
    papers: List[Dict] = []

    for p in results:
        paper_id = p.get("paperId")
        if not paper_id:
            continue

        title = (p.get("title") or "").strip()
        abstract = (p.get("abstract") or "").strip()
        authors = [a.get("name") for a in p.get("authors", []) if a.get("name")]

        # Construct PDF URL if available
        pdf_url = None
        ext_ids = p.get("externalIds", {})
        if "ArXiv" in ext_ids:
            pdf_url = f"https://arxiv.org/pdf/{ext_ids['ArXiv']}.pdf"

        papers.append({
            "source": "semantic_scholar",
            "paper_id": paper_id,                 # stable S2 ID
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "published": str(p.get("year")) if p.get("year") else None,
            "pdf_url": pdf_url,
            "metadata": p,
        })

    return papers
