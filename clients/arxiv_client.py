# clients/arxiv_client.py
import logging
import random
import time
import requests
from requests.exceptions import RequestException
from typing import Optional, Dict, Any

try:
    from defusedxml import ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"


def _parse_retry_after_seconds(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except Exception:
        return None


def _arxiv_get_with_backoff(
    url: str,
    *,
    params: Dict[str, Any],
    timeout: float,
    max_retries: int = 5,
    base_backoff_seconds: float = 2.0,
    max_backoff_seconds: float = 60.0,
):
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 429:
                retry_after = _parse_retry_after_seconds(resp.headers.get("Retry-After"))
                wait_s = retry_after if retry_after is not None else (base_backoff_seconds * (2**attempt))
                wait_s = min(max_backoff_seconds, max(3.0, wait_s))  # arXiv is IP-throttled; be conservative
                wait_s += random.uniform(0.0, 0.5)
                logging.warning(f"arXiv rate limited (429). Waiting {wait_s:.2f}s before retry...")
                time.sleep(wait_s)
                continue

            if 500 <= resp.status_code < 600:
                resp.raise_for_status()

            resp.raise_for_status()
            return resp
        except RequestException as e:
            last_exc = e
            if attempt >= max_retries:
                break
            wait_s = min(max_backoff_seconds, base_backoff_seconds * (2**attempt)) + random.uniform(0.0, 0.5)
            logging.warning(f"arXiv request failed (attempt {attempt+1}/{max_retries+1}). Retrying in {wait_s:.2f}s...")
            time.sleep(wait_s)

    if last_exc:
        raise last_exc
    raise RequestException("arXiv request failed")


def search_arxiv(query: str, max_results: int = 5):
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results
    }

    try:
        response = _arxiv_get_with_backoff(ARXIV_API_URL, params=params, timeout=30)
    except RequestException:
        logging.exception("arXiv API request failed")
        return []

    try:
        root = ET.fromstring(response.text)
    except Exception:
        logging.exception("Failed to parse arXiv API response")
        return []

    papers = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        id_elem = entry.find(f"{ATOM_NS}id")
        title_elem = entry.find(f"{ATOM_NS}title")
        summary_elem = entry.find(f"{ATOM_NS}summary")

        if not (
            id_elem is not None and id_elem.text and
            title_elem is not None and title_elem.text and
            summary_elem is not None and summary_elem.text):
            
            continue

        title = " ".join(title_elem.text.split())
        summary = " ".join(summary_elem.text.split())

        # Extract PDF link
        pdf_url = None
        for link in entry.findall(f"{ATOM_NS}link"):
            if link.get("title") == "pdf":
                pdf_url = link.get("href")
                break

        # Authors
        authors = [
            name.text
            for a in entry.findall(f"{ATOM_NS}author")
            if (name := a.find(f"{ATOM_NS}name")) is not None and name.text
        ]

        # Published date
        published = entry.find(f"{ATOM_NS}published")
        published_date = published.text if published is not None else None

        papers.append({
            "id": id_elem.text,
            "title": title,
            "summary": summary,
            "pdf_url": pdf_url,
            "authors": authors,
            "published": published_date
        })

    return papers
