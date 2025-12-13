# clients/semantic_scholar_client.py
import logging
import os
import requests
from typing import List, Dict

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

API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")


def search_semantic_scholar(query: str, limit: int = 5) -> List[Dict]:
    params = {
        "query": query,
        "limit": limit,
        "fields": ",".join(S2_FIELDS),
    }

    headers = {"x-api-key": API_KEY} if API_KEY else {}

    try:
        resp = requests.get(S2_API_URL, params=params, headers=headers, timeout=12)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Semantic Scholar request failed: {e}", exc_info=True)
        return []

    results = data.get("data", [])
    papers = []

    for p in results:
        paper_id = p.get("paperId")
        if not paper_id:
            continue

        title = (p.get("title") or "").strip()
        abstract = (p.get("abstract") or "").strip()

        authors_raw = p.get("authors") or []
        authors = [
            a.get("name").strip()
            for a in authors_raw
            if a and a.get("name")
        ]

        # PDF URL (ArXiv only)
        pdf_url = None
        ext_ids = p.get("externalIds") or {}
        if ext_ids.get("ArXiv"):
            pdf_url = f"https://arxiv.org/pdf/{ext_ids['ArXiv']}.pdf"

        papers.append({
            "source": "semantic_scholar",
            "paper_id": paper_id,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "published": str(p.get("year")) if p.get("year") else None,
            "pdf_url": pdf_url,
            "metadata": p,
        })

    return papers
