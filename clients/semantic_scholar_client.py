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
    "references",
    "citations",

]

API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")


import time
import random

def search_semantic_scholar(query: str, limit: int = 5) -> List[Dict]:
    params = {
        "query": query,
        "limit": limit,
        "fields": ",".join(S2_FIELDS),
    }

    headers = {"x-api-key": API_KEY} if API_KEY else {}
    
    max_retries = 1
    base_delay = 1

    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(S2_API_URL, params=params, headers=headers, timeout=5)
            
            if resp.status_code == 429:
                wait_time = int(resp.headers.get("Retry-After", base_delay * (2 ** attempt)))
                # Cap wait time to avoid hanging too long
                wait_time = min(wait_time, 5)
                # Add jitter
                wait_time += random.uniform(0, 0.5)
                
                logger.warning(f"⚠️ S2 Rate Limit (429). Retrying in {wait_time:.2f}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
                continue
                
            resp.raise_for_status()
            data = resp.json()
            break # Success
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # Should be handled above, but just in case raise_for_status catches it first
                logger.warning(f"⚠️ S2 Rate Limit hit via HTTPError: {e}")
                time.sleep(5)
                continue
            logger.error(f"Semantic Scholar HTTP error: {e}")
            return []
            
        except Exception as e:
            logger.error(f"Semantic Scholar request failed: {e}", exc_info=True)
            return []
    else:
        logger.error("❌ Semantic Scholar: Max retries exceeded.")
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
            "references": p.get("references", []),
            "citations": p.get("citations", []),
            "metadata": p,
        })

    return papers
