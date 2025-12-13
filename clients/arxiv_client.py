# clients/arxiv_client.py
import logging
import requests
from requests.exceptions import RequestException

try:
    from defusedxml import ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"


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
