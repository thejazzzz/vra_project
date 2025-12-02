# File: clients/arxiv_client.py
import logging
import requests
from requests.exceptions import RequestException

# Prefer defusedxml to mitigate XXE risks when parsing untrusted XML.
try:
    from defusedxml import ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET  # fallback (less safe)

ARXIV_API_URL = "https://export.arxiv.org/api/query"

def search_arxiv(query: str, max_results: int = 5):
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results
    }

    try:
        response = requests.get(ARXIV_API_URL, params=params, timeout=10)
        response.raise_for_status()
    except RequestException:
        logging.exception("arXiv API request failed")
        return []  # Network issue → return empty list

    try:
        root = ET.fromstring(response.text)
    except Exception:
        logging.exception("Failed to parse arXiv API response")
        return []  # Bad XML → return empty list

    papers = []
    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        id_elem = entry.find("{http://www.w3.org/2005/Atom}id")
        title_elem = entry.find("{http://www.w3.org/2005/Atom}title")
        summary_elem = entry.find("{http://www.w3.org/2005/Atom}summary")

        # Skip incomplete entries safely
        if not (id_elem is not None and title_elem is not None and summary_elem is not None):
            continue

        papers.append({
            "id": id_elem.text or "",
            "title": (title_elem.text or "").strip(),
            "summary": (summary_elem.text or "").strip(),
        })

    return papers
