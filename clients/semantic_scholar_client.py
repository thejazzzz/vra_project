# clients/semantic_scholar_client.py
import logging
import os
import requests
import time
import threading
import email.utils
from datetime import datetime, timezone
import random
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------

S2_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

# Enhanced fields for better graph data and PDF access
S2_FIELDS = [
    "paperId",
    "title",
    "abstract",
    "authors",
    "year",
    "venue",
    "externalIds",
    "url",
    "referenceCount",
    "citationCount",
    "influentialCitationCount",
    "openAccessPdf",  # Crucial for direct downloads
    "references.paperId",
    "references.title",
    "references.year",
    # Citations can be voluminous; fetching just counts is safer for search list.
    # We can fetch specific details in a separate 'details' call if needed.
    # "citations.paperId", "citations.title" 
]

API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

# -----------------------------------------------------------------------------
# RATE LIMITER (1 req / second)
# -----------------------------------------------------------------------------

class RateLimiter:
    def __init__(self, requests_per_second: float = 1.0):
        self.delay = 1.0 / requests_per_second
        self.last_request_time = 0.0
        self._lock = threading.Lock()

    def wait(self):
        with self._lock:
            current_time = time.time()
            elapsed = current_time - self.last_request_time
            if elapsed < self.delay:
                sleep_time = self.delay - elapsed
                time.sleep(sleep_time)
            self.last_request_time = time.time()

# Global limiter instance
_limiter = RateLimiter(requests_per_second=1.0) # Conservative 1.0 RPS (matches user req)

# -----------------------------------------------------------------------------
# CLIENT FUNCTIONS
# -----------------------------------------------------------------------------

def search_semantic_scholar(query: str, limit: int = 5) -> List[Dict]:
    """
    Search Semantic Scholar for papers matching the query.
    Enforces 1 req/sec rate limit.
    """
    params = {
        "query": query,
        "limit": limit,
        "fields": ",".join(S2_FIELDS),
    }

    headers = {"x-api-key": API_KEY} if API_KEY else {}
    
    max_retries = 2
    base_backoff = 2

    # Enforce Rate Limit before request
    _limiter.wait()

    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(S2_API_URL, params=params, headers=headers, timeout=20)
            if resp.status_code == 429:
                # Server-side rate limit hit despite our client-side limit
                retry_after = resp.headers.get("Retry-After")
                wait_time = 0.0

                if retry_after:
                    try:
                        wait_time = float(retry_after)
                    except ValueError:
                        try:
                            # Parse HTTP-date format
                            date_time = email.utils.parsedate_to_datetime(retry_after)
                            wait_time = (date_time - datetime.now(timezone.utc)).total_seconds()
                        except Exception:
                             wait_time = base_backoff * (2 ** attempt)

                if wait_time < 0: wait_time = 0.0
                
                # Fallback if header missing or parsing failed completely (and not set by exception)
                if not wait_time:
                     wait_time = base_backoff * (2 ** attempt)

                wait_time = min(wait_time, 10) # Cap at 10s
                wait_time += random.uniform(0, 0.5) # Add jitter

                logger.warning(f"⚠️ S2 API Rate Limit (429). Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
                _limiter.wait() # Reset local timer logic
                continue
                
            resp.raise_for_status()
            data = resp.json()
            break 
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries:
                logger.error(f"Semantic Scholar Error (Final): {e}")
                return []
            logger.warning(f"Semantic Scholar Error: {e}. Retrying...")
            time.sleep(1)
            _limiter.wait()
            
        except Exception as e:
            logger.error(f"Unexpected error in S2 search: {e}", exc_info=True)
            return []
    else:
        return []

    # Process Results
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
            a.get("name").strip() for a in authors_raw if a and a.get("name")
        ]

        # Prioritize OpenAccessPDF if available, else fallback to ArXiv
        pdf_url = None
        
        # 1. Check openAccessPdf
        oa_pdf = p.get("openAccessPdf")
        if oa_pdf and isinstance(oa_pdf, dict):
             pdf_url = oa_pdf.get("url")
        
        # 2. Fallback to ArXiv External ID
        if not pdf_url:
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
            "citation_count": p.get("citationCount", 0),
            "reference_count": p.get("referenceCount", 0),
            "references": p.get("references", []), # List of dicts {paperId, title, year}
            "metadata": p,
        })

    return papers
