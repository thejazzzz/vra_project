# File: services/research_service.py
import asyncio
import logging
import fitz  # PyMuPDF
from typing import Dict, List, Tuple, Optional

from clients.arxiv_client import search_arxiv
from clients.chroma_client import get_client
from database.db import SessionLocal
from database.models.paper_model import Paper
from utils.sanitization import clean_text, is_nonempty_text

logger = logging.getLogger(__name__)


def normalize_arxiv_id(raw_id: str) -> str:
    """Normalize arXiv ID to final value only, e.g.
    'http://arxiv.org/abs/2306.11113v2' -> '2306.11113v2'
    """
    if not raw_id:
        return ""
    return raw_id.split("/")[-1].strip()


def clean_pdf_text(text: str) -> str:
    """
    Clean PDF extracted text using the shared sanitizer.
    """
    return clean_text(text)


async def download_and_extract_pdf(pdf_url: str) -> str:
    """Download PDF async and extract text using PyMuPDF.
    Returns extracted text or '' if failed.
    """
    if not pdf_url:
        return ""

    try:
        import aiohttp

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        }

        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.get(pdf_url, timeout=25) as resp:
                if resp.status != 200:
                    logger.warning(f"PDF download failed: {resp.status} | {pdf_url}")
                    return ""
                pdf_bytes = await resp.read()

        def extract():
            try:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                pages = [page.get_text("text") for page in doc]
                doc.close()
                return "\n".join(pages)
            except Exception as e:
                logger.error(f"PyMuPDF failed for {pdf_url}: {e}")
                return ""

        raw_text = await asyncio.to_thread(extract)
        return clean_pdf_text(raw_text)

    except Exception as e:
        logger.warning(f"PDF fetch error: {pdf_url} | {e}")
        return ""


async def process_research_task(query: str) -> Dict:
    db = SessionLocal()
    stored_entries: List[Tuple[Paper, dict]] = []
    failed_storage: List[str] = []
    failed_embedding: List[str] = []
    papers: List[Dict] = []
    error_message: Optional[str] = None

    try:
        vector_client = get_client()

        # Fetch metadata from arXiv
        try:
            papers = await asyncio.to_thread(search_arxiv, query)
        except Exception as e:
            logger.error(f"arXiv search failed: {e}", exc_info=True)
            return {
                "success": False,
                "query": query,
                "papers_found": 0,
                "error": "Failed to fetch papers from arXiv",
            }

        if not papers:
            return {
                "success": True,
                "query": query,
                "papers_found": 0,
                "storage_failed": [],
                "embedding_failed": [],
                "papers": []
            }

        logger.info(f"Fetched {len(papers)} papers from arXiv")

        # Download PDFs asynchronously
        pdf_tasks = [download_and_extract_pdf(p.get("pdf_url")) for p in papers]
        pdf_texts = await asyncio.gather(*pdf_tasks)

        # Store in DB
        for paper, fulltext in zip(papers, pdf_texts):
            raw_id = paper.get("id")
            paper_id = normalize_arxiv_id(raw_id)
            if not paper_id:
                failed_storage.append("unknown")
                continue

            paper["id"] = paper_id
            paper["title"] = clean_text(paper.get("title", "Untitled Paper"))
            paper["summary"] = clean_text(paper.get("summary", ""))

            clean_text_body = clean_pdf_text(fulltext)

            try:
                existing = (
                    db.query(Paper)
                    .filter(Paper.paper_id == paper_id)
                    .one_or_none()
                )

                if existing:
                    existing.raw_text = clean_text_body or existing.raw_text
                    if is_nonempty_text(paper["summary"]):
                        existing.abstract = paper["summary"]
                    existing.paper_metadata = paper
                    db_obj = existing
                else:
                    db_obj = Paper(
                        paper_id=paper_id,
                        title=paper["title"],
                        abstract=paper["summary"],
                        raw_text=clean_text_body,
                        paper_metadata=paper
                    )
                    db.add(db_obj)

                db.commit()
                stored_entries.append((db_obj, paper))
            except Exception as e:
                logger.error(f"Failed to store paper {paper_id}: {e}", exc_info=True)
                db.rollback()
                failed_storage.append(paper_id)
                continue

            try:
                db.refresh(db_obj)
            except Exception as e:
                logger.warning(f"Failed to refresh paper {paper_id}: {e}")

        # Embed abstracts in Chroma
        embedding_tasks = []
        entries_with_embeddings = []

        for db_paper, paper_meta in stored_entries:
            if not is_nonempty_text(db_paper.abstract):
                continue

            chroma_id = f"paper-{db_paper.id}"
            task = asyncio.to_thread(
                vector_client.store,
                chroma_id,
                db_paper.abstract,
                {"paper_db_id": db_paper.id, "paper_id": db_paper.paper_id},
            )
            embedding_tasks.append(task)
            entries_with_embeddings.append((db_paper, paper_meta))

        if embedding_tasks:
            results = await asyncio.gather(*embedding_tasks, return_exceptions=True)
            for entry, result in zip(entries_with_embeddings, results):
                if isinstance(result, Exception):
                    failed_embedding.append(entry[0].paper_id)

    except Exception as e:
        logger.error(f"Unexpected error in process_research_task: {e}", exc_info=True)
        error_message = str(e)

    finally:
        db.close()

    return {
        "success": error_message is None,
        "query": query,
        "papers_found": len(stored_entries),
        "storage_failed": failed_storage,
        "embedding_failed": failed_embedding,
        "db_ids": [db_paper.id for db_paper, _ in stored_entries],
        "papers": papers,
        "error": error_message,
    }

