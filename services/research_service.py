# File: services/research_service.py

import asyncio
import logging
import fitz
import hashlib
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm.attributes import flag_modified

from agents.data_acquisition_agent import data_acquisition_agent
from utils.id_normalization import build_canonical_id
from database.db import SessionLocal
from database.models.paper_model import Paper
from utils.sanitization import clean_text, is_nonempty_text
from clients.chroma_client import get_client

logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# PDF DOWNLOAD + EXTRACTION
# ------------------------------------------------------------
async def download_pdf(pdf_url: Optional[str]) -> str:
    if not pdf_url:
        return ""

    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(pdf_url, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"PDF download failed ({resp.status}): {pdf_url}")
                    return ""
                pdf_bytes = await resp.read()
    except Exception as e:
        logger.warning(f"PDF request failed for {pdf_url}: {e}")
        return ""

    def extract():
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text = "\n".join(page.get_text("text") for page in doc)
            doc.close()
            return clean_text(text)
        except Exception as e:
            logger.warning(f"PDF extraction error: {e}")
            return ""

    return await asyncio.to_thread(extract)


# ------------------------------------------------------------
# MAIN PIPELINE
# ------------------------------------------------------------
async def process_research_task(query: str) -> Dict:
    """
    PIPELINE:
    1. Multi-source acquisition
    2. Deduplication (handled upstream)
    3. PDF extraction
    4. DB upsert (merged metadata + hash dedupe)
    5. Vector embeddings (Chroma)
    """
    db = SessionLocal()

    stored: List[Tuple[Paper, dict]] = []
    failed_storage = []
    failed_embedding = []
    error_message = None

    try:
        # --------------------------------------------
        # 1. Fetch merged papers
        # --------------------------------------------
        papers = await data_acquisition_agent.run(query, limit=5)

        if not papers:
            return {
                "success": True,
                "query": query,
                "papers_found": 0,
                "storage_failed": [],
                "embedding_failed": [],
                "db_ids": [],
                "papers": []
            }

        logger.info(f"📄 Papers after dedupe+merge: {len(papers)}")

        # --------------------------------------------
        # 2. PDF extraction async
        # --------------------------------------------
        pdf_tasks = [download_pdf(p.get("pdf_url")) for p in papers]
        pdf_texts = await asyncio.gather(*pdf_tasks)

        vector_client = get_client()

        # --------------------------------------------
        # 3. DB UPSERT (NO COMMIT INSIDE LOOP)
        # --------------------------------------------
        for paper, fulltext in zip(papers, pdf_texts):

            title = clean_text(paper.get("title", "Untitled"))
            abstract = clean_text(paper.get("summary", ""))

            canonical_id = paper.get("canonical_id")
            
            # Fallback if somehow missing (e.g. direct call bypassing merger)
            if not canonical_id:
                canonical_id = build_canonical_id(
                    primary_id=paper.get("id"),
                    title=title,
                    source=paper.get("source")
                )
            
            if not canonical_id:
                logger.error(f"❌ Skipping paper '{title[:30]}...' - Could not generate canonical_id")
                failed_storage.append({"error": "missing_canonical_id", "title": title[:50], "source": paper.get("source")})
                continue
            try:
                existing = (
                    db.query(Paper)
                    .filter(Paper.canonical_id == canonical_id)
                    .one_or_none()
                )

                # =====================================================
                # CASE A — UPDATE EXISTING ROW
                # =====================================================
                if existing:

                    src = paper.get("source")
                    if src:
                        existing.paper_metadata[src] = paper
                        flag_modified(existing, "paper_metadata")

                    if is_nonempty_text(abstract):
                        existing.abstract = abstract

                    # -------- HASH-BASED DEDUPLICATION --------
                    if fulltext:
                        content_hash = hashlib.md5(fulltext.encode()).hexdigest()
                        existing_hashes = existing.paper_metadata.get("pdf_hashes", [])

                        if content_hash not in existing_hashes:
                            existing.raw_text = (existing.raw_text or "") + "\n" + fulltext
                            existing_hashes.append(content_hash)
                            existing.paper_metadata["pdf_hashes"] = existing_hashes
                            flag_modified(existing, "paper_metadata")

                    db_obj = existing

                # =====================================================
                # CASE B — INSERT NEW PAPER
                # =====================================================
                else:
                    hashes = []
                    if fulltext:
                        hashes.append(hashlib.md5(fulltext.encode()).hexdigest())

                    db_obj = Paper(
                        canonical_id=canonical_id,
                        paper_id=paper.get("id"),   # backward compatibility
                        title=title,
                        abstract=abstract,
                        raw_text=fulltext,
                        published_year=paper.get("year"), # Explicitly set column
                        arxiv_id=paper.get("paper_id") if paper.get("source") == "arxiv" else None,
                        paper_metadata={
                            paper.get("source", "unknown"): paper,
                            "pdf_hashes": hashes,
                            "year": paper.get("year"), # redundant but safe
                            "authors": paper.get("authors", [])
                        },
                    )
                    db.add(db_obj)

                stored.append((db_obj, paper))

            except Exception as e:
                logger.error(f"❌ DB write failed for {canonical_id}: {e}", exc_info=True)
                db.rollback()
                failed_storage.append(canonical_id)
                continue

        # --------------------------------------------
        # 3B. BATCH COMMIT (IMPORTANT!)
        # --------------------------------------------
        if stored:
            db.commit()
            for db_obj, _ in stored:
                db.refresh(db_obj)

        # --------------------------------------------
        # 4. CHROMA EMBEDDINGS — CORRECT ALIGNMENT
        # --------------------------------------------
        papers_to_embed = []

        for db_obj, _ in stored:
            if is_nonempty_text(db_obj.abstract):
                chroma_id = f"paper-{db_obj.id}"
                papers_to_embed.append((db_obj, chroma_id))

        if papers_to_embed:
            embed_tasks = [
                asyncio.to_thread(
                    vector_client.store,
                    chroma_id,
                    db_obj.abstract,
                    {"paper_db_id": db_obj.id, "canonical_id": db_obj.canonical_id},
                )
                for db_obj, chroma_id in papers_to_embed
            ]

            results = await asyncio.gather(*embed_tasks, return_exceptions=True)

            for (db_obj, _), result in zip(papers_to_embed, results):
                if isinstance(result, Exception):
                    failed_embedding.append(db_obj.canonical_id)

    except Exception as e:
        error_message = str(e)
        logger.error(f"🚨 UNEXPECTED ERROR: {e}", exc_info=True)

    finally:
        db.close()

    # --------------------------------------------
    # FINAL RESULT
    # --------------------------------------------
    return {
        "success": error_message is None,
        "query": query,
        "papers_found": len(stored),
        "storage_failed": failed_storage,
        "embedding_failed": failed_embedding,
        "db_ids": [db_obj.id for db_obj, _ in stored],
        # Return the ENRICHED papers from the DB, not the raw input `papers`
        # This ensures we get the extracted abstract/fulltext if available
        "papers": [
            {
                "canonical_id": db_obj.canonical_id,
                "title": db_obj.title,
                "abstract": db_obj.abstract, # The critical field
                "source": db_obj.paper_metadata.get("source", "unknown"),
                "url": db_obj.paper_metadata.get("url"),
                "year": db_obj.paper_metadata.get("year"),
                "authors": db_obj.paper_metadata.get("authors", []),
                "citation_count": db_obj.paper_metadata.get("citation_count", 0),
                "venue": db_obj.paper_metadata.get("venue"),
            }
            for db_obj, _ in stored
        ],
        "error": error_message,
    }


async def add_manual_paper(
    query: str,
    title: str,
    abstract: str,
    url: str = "",
    authors: List[str] = [],
    year: int = 2024,
    source: str = "user_upload"
) -> Dict:
    """
    Manually add a paper to the database and vector store.
    """
    db = SessionLocal()
    try:
        # Generate Canonical ID
        canonical_id = build_canonical_id(
            primary_id=url or title, # Use title as fallback if no URL
            title=title,
            source=source
        )
        
        # Check if exists
        existing = db.query(Paper).filter(Paper.canonical_id == canonical_id).one_or_none()
        
        if existing:
            # Update abstract if provided and missing
            if not existing.abstract and abstract:
                existing.abstract = abstract
                flag_modified(existing, "paper_metadata")
            
            db_obj = existing
        else:
            # Create new
            db_obj = Paper(
                canonical_id=canonical_id,
                paper_id=f"manual_{hashlib.md5(title.encode()).hexdigest()[:8]}",
                title=title,
                abstract=abstract,
                raw_text=abstract, # Treat abstract as raw text for now
                paper_metadata={
                    "source": source,
                    "url": url,
                    "authors": authors,
                    "year": year,
                    "manual_entry": True
                }
            )
            db.add(db_obj)
        
        db.commit()
        db.refresh(db_obj)

        # Embed in Chroma
        vector_client = get_client()
        chroma_id = f"paper-{db_obj.id}"
        vector_client.store(
            chroma_id,
            abstract,
            {"paper_db_id": db_obj.id, "canonical_id": db_obj.canonical_id}
        )
        
        return {
            "success": True,
            "paper": {
                "canonical_id": db_obj.canonical_id,
                "title": db_obj.title,
                "abstract": db_obj.abstract,
                "source": source,
                "url": url,
                "year": year,
                "authors": authors
            }
        }

    except Exception as e:
        logger.error(f"Failed to add manual paper: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        db.close()
