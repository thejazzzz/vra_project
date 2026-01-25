# File: services/research_service.py

import asyncio
import logging
import fitz
import hashlib
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm.attributes import flag_modified

from agents.data_acquisition_agent import data_acquisition_agent
from utils.id_normalization import build_canonical_id, to_canonical_id
from database.db import SessionLocal
from database.models.paper_model import Paper
from utils.sanitization import clean_text, is_nonempty_text
from clients.chroma_client import get_client
from services.llm_factory import LLMFactory, LLMProvider
from services.progress_tracker import ProgressTracker, ResearchPhase
import uuid


logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# PDF DOWNLOAD + EXTRACTION
# ------------------------------------------------------------
# ------------------------------------------------------------
# PDF DOWNLOAD + EXTRACTION (STEALTH MODE)
# ------------------------------------------------------------
import random

# A. User-Agent Rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

import threading

# C. Hard Concurrency Cap
PDF_SEMAPHORE: Optional[asyncio.Semaphore] = None
_INIT_LOCK = threading.Lock()

def get_random_header():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/pdf,application/x-download,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extracts text from PDF bytes using PyMuPDF (fitz).
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "\n".join(page.get_text("text") for page in doc)
        doc.close()
        return clean_text(text)
    except Exception as e:
        logger.warning(f"PDF extraction error: {e}")
        return ""

async def download_pdf(pdf_url: Optional[str]) -> str:
    if not pdf_url:
        return ""

    import aiohttp
    
    # D. Respect arXiv etiquette
    if "arxiv.org" in pdf_url:
        import os
        contact_email = os.environ.get("ARXIV_CONTACT_EMAIL", "admin@example.com")
        headers = {
            "User-Agent": f"VRA_Research_Assistant/1.0 (mailto:{contact_email})",
            "Accept": "application/pdf"
        }
    else:
        headers = get_random_header()

    global PDF_SEMAPHORE
    
    # Safe Lazy Initialization
    if PDF_SEMAPHORE is None:
        with _INIT_LOCK:
            if PDF_SEMAPHORE is None:
                PDF_SEMAPHORE = asyncio.Semaphore(1)

    for attempt in range(3):
        try:
            # Rotate UA on retry for non-arxiv
            if attempt > 0 and "arxiv.org" not in pdf_url:
                    headers = get_random_header()

            timeout = aiohttp.ClientTimeout(total=45)
            
            # CRITICAL: Only hold semaphore during actual network request
            async with PDF_SEMAPHORE: 
                async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                    async with session.get(pdf_url) as resp:
                        status = resp.status
                        if status == 200:
                            # Check content type if possible
                            pdf_bytes = await resp.read()

            # Process outside semaphore (CPU bound or just flow logic)
            if status == 200:
                if len(pdf_bytes) < 1000: 
                    logger.warning(f"Downloaded file too small ({len(pdf_bytes)}b) for {pdf_url}")
                    return ""
                return await asyncio.to_thread(extract_text_from_pdf_bytes, pdf_bytes)
            
            # B. Smart Retry Policy (OUTSIDE Semaphore)
            elif status == 429: # Rate Limit
                delay = (2 ** attempt) + random.uniform(3, 8)
                logger.warning(f"🛑 Rate limited (429) for {pdf_url}. Backoff {delay:.2f}s...")
                await asyncio.sleep(delay)
                continue
                
            elif status == 403: # Forbidden
                delay = (2 ** attempt) + random.uniform(5, 10)
                logger.warning(f"🚫 Access Forbidden (403) for {pdf_url}. Retrying with new UA in {delay:.2f}s...")
                await asyncio.sleep(delay)
                continue
                
            elif status in [500, 502, 503, 504]: # Server Error
                delay = (1.5 ** attempt) + random.uniform(1, 3)
                logger.warning(f"Server error ({status}) for {pdf_url}. Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
                continue
                
            else:
                logger.warning(f"PDF download failed ({status}): {pdf_url}")
                return ""
                
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            delay = (2 ** attempt) + random.uniform(1, 3)
            logger.warning(f"Network error for {pdf_url} (Attempt {attempt+1}): {e}. Retrying in {delay:.2f}s...")
            await asyncio.sleep(delay)
        except Exception as e:
            logger.error(f"Unexpected error downloading {pdf_url}: {e}")
            return ""

    return ""


# ------------------------------------------------------------
# HELPER: QUERY EXPANSION
# ------------------------------------------------------------
async def generate_sub_queries(query: str) -> List[str]:
    """
    Generates 3-6 semantic sub-queries using LLM to broaden research scope.
    Tries OpenAI first, then OpenRouter as fallback.
    """
    system_prompt = (
        "You are a Senior Research Assistant. Your task is to generate 3-6 specific, academic search queries "
        "related to the user's topic to perform a comprehensive literature review.\n"
        "Rules:\n"
        "1. Queries must be broader or orthogonal to the main topic.\n"
        "2. Avoid speculative or non-academic phrasing.\n"
        "3. Return ONLY the queries, one per line.\n"
        "4. Do not number the lines."
    )

    async def _try_generate(provider: str) -> List[str]:
        try:
            client = LLMFactory.get_client(provider)
            model = LLMFactory.get_default_model(provider)
            
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Topic: {query}"}
                ],
                temperature=0.3
            )
            text = response.choices[0].message.content.strip()
            return [q.strip() for q in text.split('\n') if q.strip()]
        except Exception as e:
            logger.warning(f"Query generation failed with {provider}: {e}")
            raise e

    # Attempt 1: Default/OpenAI
    try:
        queries = await _try_generate(LLMFactory.OPENAI)
        return queries[:6]
    except Exception:
        pass

    # Attempt 2: OpenRouter
    try:
        queries = await _try_generate(LLMFactory.OPENROUTER)
        logger.info("Used OpenRouter fallback for query expansion.")
        return queries[:6]
    except Exception:
        pass
        
    logger.error("All LLM providers failed for query expansion.")
    return []

# ------------------------------------------------------------
# HELPER: SMART DEDUPLICATION
# ------------------------------------------------------------
def _smart_deduplicate(papers: List[Dict]) -> List[Dict]:
    """
    Deduplicates papers based on strict priority:
    1. Semantic Scholar ID (s2)
    2. DOI
    3. Normalized Title + Year
    
    Re-assigns canonical_id and merges metadata.
    """
    # Map key -> Paper
    # We will use a disjoint-set (union-find) style or simply iterative merging?
    # Since we want to merge metadata, iterative is better.
    
    # 1. Build Index by Priority Keys
    # We'll use a unique internal ID for each cluster of papers
    
    clusters: Dict[str, Dict] = {} # cluster_id -> merged_paper
    
    # Pointer maps to find cluster
    s2_map: Dict[str, str] = {}
    doi_map: Dict[str, str] = {}
    title_map: Dict[str, str] = {}
    
    for p in papers:
        # Extract Keys
        meta = p.get("metadata", {})
        
        s2_id = p.get("paper_id") if p.get("source") == "semantic_scholar" else meta.get("paperId")
        # Check externalIds for S2
        if not s2_id and "externalIds" in meta:
             s2_id = meta["externalIds"].get("CorpusId") # Sometimes S2 puts it here? No, paperId is main.
       
        doi = meta.get("doi") or meta.get("DOI")
        if not doi and "externalIds" in meta:
            doi = meta["externalIds"].get("DOI")
            
        # Title+Year Key
        t = clean_text(p.get("title", "")).lower()
        y = str(p.get("year") or p.get("publication_year") or "0000")
        ty_key = f"{t}|{y}"
        
        # Determine strict canonical ID for this paper (local)
        # We need to see if it matches any EXISTING cluster
        cluster_id = None
        
        if s2_id and str(s2_id) in s2_map:
            cluster_id = s2_map[str(s2_id)]
        elif doi and str(doi) in doi_map:
            cluster_id = doi_map[str(doi)]
        elif ty_key in title_map:
            cluster_id = title_map[ty_key]
            
        if not cluster_id:
            # Create new cluster
            cluster_id = str(uuid.uuid4())
            clusters[cluster_id] = p
        else:
            # Merge into existing
            existing = clusters[cluster_id]
            
            # Merge sources
            srcs = set(existing.get("sources", [existing.get("source")]))
            srcs.add(p.get("source"))
            if p.get("sources"):
                 srcs.update(p.get("sources"))
            existing["sources"] = list(srcs)
            
            # Keep the "best" metadata (S2 > Arxiv)
            if p.get("source") == "semantic_scholar" and existing.get("source") != "semantic_scholar":
                # Upgrade to S2 base
                # But keep description if S2 abstract is empty?
                # data_merger_agent already handles logic, but let's be simple:
                # Prefer S2 ID
                existing["source"] = "semantic_scholar"
                existing["paper_id"] = s2_id or p.get("paper_id")
                existing.setdefault("metadata", {}).update(p.get("metadata", {}))
            
            # Merge abstracts (longest wins)
            if len(p.get("summary", "")) > len(existing.get("summary", "")):
                existing["summary"] = p.get("summary")
            
            clusters[cluster_id] = existing

        # Update Maps
        if s2_id: s2_map[str(s2_id)] = cluster_id
        if doi: doi_map[str(doi)] = cluster_id
        title_map[ty_key] = cluster_id
        
    # Re-generate Canonical IDs
    final_list = []
    for cid, p in clusters.items():
        # Enforce Rule: S2 > DOI > Title
        # Check keys in finalized object
        meta = p.get("metadata", {})
        s2_id = p.get("paper_id") if p.get("source") == "semantic_scholar" else meta.get("paperId")
        doi = meta.get("doi") or meta.get("DOI")
        
        new_canonical = None
        if s2_id:
            new_canonical = to_canonical_id("semantic_scholar", str(s2_id))
        elif doi:
            # We don't have a direct "doi:" prefix usually, 
            # `to_canonical_id` handles specific sources.
            # But we can fallback to using DOI as ID.
            new_canonical = f"doi:{doi}"
        else:
            new_canonical = p.get("canonical_id") # Fallback to original
             
        if new_canonical:
            p["canonical_id"] = new_canonical
        elif not p.get("canonical_id"):
            # Fallback if no canonical ID exists at all
            p["canonical_id"] = f"fallback:{uuid.uuid4()}"
            
        final_list.append(p)
        
    return final_list


# ------------------------------------------------------------
# MAIN PIPELINE
# ------------------------------------------------------------
async def process_research_task(
    query: str, 
    include_paper_ids: Optional[List[str]] = None,
    task_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict:
    """
    PIPELINE:
    0. Fetch explicitly included local papers
    1. Multi-source acquisition (External) with Adaptive Expansion
    2. Smart Deduplication
    3. PDF extraction
    4. DB upsert (merged metadata + hash dedupe)
    5. Vector embeddings (Chroma)
    """
    if include_paper_ids is None:
        include_paper_ids = []
    
    # Setup Progress Tracking
    if not task_id:
        task_id = str(uuid.uuid4())
    
    progress = ProgressTracker.start_task(task_id, user_id=user_id)
    progress.update(phase=ResearchPhase.INITIALIZING, queries_total=1) # Start with 1 (main)

    db = SessionLocal()

    stored: List[Tuple[Paper, dict]] = []
    failed_storage = []
    failed_embedding = []
    saved_db_objects = [] # Initialized early for safety
    error_message = None
    
    # Final list of papers to process
    papers_to_process = []

    try:
        # --------------------------------------------
        # 0. Load Included Papers (Local)
        # --------------------------------------------
        if include_paper_ids:
            logger.info(f"Including {len(include_paper_ids)} local papers")
            local_papers_db = db.query(Paper).filter(Paper.id.in_(include_paper_ids)).all()
            for lp in local_papers_db:
                lp_dict = {
                    "canonical_id": lp.canonical_id,
                    "id": lp.paper_id,
                    "title": lp.title,
                    "summary": lp.abstract,
                    "pdf_url": None,
                    "source": lp.paper_metadata.get("source", "local_file"),
                    "sources": ["local_file"],
                    "year": lp.published_year or 2024,
                    "authors": lp.paper_metadata.get("authors", []),
                    "metadata": lp.paper_metadata,
                    "_is_local": True
                }
                papers_to_process.append(lp_dict)

        # --------------------------------------------
        # 1. Adaptive Data Acquisition
        # --------------------------------------------
        progress.update(phase=ResearchPhase.FETCHING_PAPERS)
        
        # A. Initial Fetch (Main Query)
        logger.info(f"🔍 Running initial fetch for: {query}")
        main_results = await data_acquisition_agent.run(query, limit=50)
        
        MIN_PAPERS_FOR_EXPANSION = 5
        run_expansion = False
        
        if len(main_results) < MIN_PAPERS_FOR_EXPANSION:
            logger.info(f"📉 Low result count ({len(main_results)}). Triggering expansion.")
            run_expansion = True
        else:
            logger.info(f"✅ Sufficient results ({len(main_results)}). Skipping expansion.")
             
        collected_papers = main_results
        
        # Track Progress
        current_found = len(main_results)
        progress.update(
            queries_completed=1, 
            papers_found=current_found
        )

        if run_expansion:
            progress.update(phase=ResearchPhase.EXPANDING_QUERIES)
            
            sub_queries = await generate_sub_queries(query)
            logger.info(f"🧠 Generated sub-queries: {sub_queries}")
            
            if sub_queries:
                progress.update(
                    queries_total=1 + len(sub_queries),
                    phase=ResearchPhase.FETCHING_PAPERS
                )
                
                # Run concurrently
                tasks = [data_acquisition_agent.run(sq, limit=20) for sq in sub_queries]
                
                # Robust Execution: Gather return_exceptions=True? 
                # data_acquisition_agent handles logic but catch here too basically.
                results_list = await asyncio.gather(*tasks, return_exceptions=True)
                
                for idx, res in enumerate(results_list):
                    if isinstance(res, Exception):
                        logger.error(f"Expansion query failed: {sub_queries[idx]} - {res}")
                        progress.update(
                            queries_failed=progress.queries_failed + 1,
                            queries_completed=progress.queries_completed + 1,
                            papers_found=current_found
                        )
                    else:
                        # Tag Results
                        for p in res:
                            if "metadata" not in p: p["metadata"] = {}
                            # Set at top level for easy access during upsert promotion
                            p["origin"] = "query_expansion"
                            p["source_query"] = sub_queries[idx]
                            # Also keep in metadata for provenance
                            p["metadata"]["origin"] = "query_expansion"
                            p["metadata"]["source_query"] = sub_queries[idx]
                        
                        collected_papers.extend(res)
                        current_found += len(res)
                    
                        progress.update(
                            queries_completed=progress.queries_completed + 1,
                            papers_found=current_found
                        )
        
        # --------------------------------------------
        # 2. Smart Deduplication
        # --------------------------------------------
        progress.update(phase=ResearchPhase.MERGING_RESULTS)
        
        # Combine local (already process) + fetched
        # But wait, local papers shouldn't be deduped against external by ID? 
        # Yes they should. If I uploaded X and it finds X online, merging is good.
        all_raw = papers_to_process + collected_papers
        
        final_papers = _smart_deduplicate(all_raw)
        
        logger.info(f"📄 Papers after Smart Dedupe: {len(all_raw)} -> {len(final_papers)}")
        
        progress.update(papers_found=len(final_papers)) # Update with distinct count
        
        papers = final_papers
        
        if not papers:
            progress.update(phase=ResearchPhase.COMPLETED)
            return {
                "success": True, 
                "task_id": task_id,
                "papers_found": 0, 
                "papers": [],
                "phases": progress.to_dict(),
                "storage_failed": [],
                "embedding_failed": [],
                "db_ids": [],
                "error": None
            } 

        # --------------------------------------------
        # 3. Store Metadata & Start Background Download in parallel
        # --------------------------------------------
        
        # We save metadata FIRST so user sees papers immediately
        saved_db_objects = []
        for paper in papers:
            # 3a. Prepare DB Object
            title = clean_text(paper.get("title", "Untitled"))
            abstract = clean_text(paper.get("summary", ""))
            canonical_id = paper.get("canonical_id")
            
            # Fallback ID
            if not canonical_id:
                canonical_id = build_canonical_id(
                    primary_id=paper.get("id"),
                    title=title,
                    source=paper.get("source")
                )
            
            try:
                # Upsert Logic (Simplified for metadata first)
                existing = db.query(Paper).filter(Paper.canonical_id == canonical_id).one_or_none()
                
                # Metadata to merge
                pm = paper.get("metadata", {}) or {}
                # Initialize tracking if new
                if "pdf_status" not in pm: pm["pdf_status"] = "queued"
                if "pdf_attempts" not in pm: pm["pdf_attempts"] = 0
                
                if existing:
                    # Merge metadata
                    existing.paper_metadata = {**existing.paper_metadata, **pm}
                    flag_modified(existing, "paper_metadata")
                    if is_nonempty_text(abstract): existing.abstract = abstract
                    db_obj = existing
                else:
                    db_obj = Paper(
                        canonical_id=canonical_id,
                        paper_id=paper.get("id"),
                        title=title,
                        abstract=abstract,
                        published_year=paper.get("year"),
                        paper_metadata=pm
                    )
                    db.add(db_obj)
                
                saved_db_objects.append(db_obj)
                
            except Exception as e:
                logger.error(f"Metadata save failed for {title}: {e}")
                failed_storage.append(canonical_id)

        db.commit()
        for obj in saved_db_objects: db.refresh(obj) # Get IDs
        
        # 3b. Fire Background Task (Fire-and-Forget)
        # We pass the IDs so the background worker can re-fetch safe objects
        paper_ids_map = {p.id: p.canonical_id for p in saved_db_objects}
        
        # Start background loop
        # Guard against crash / log exceptions
        bg_task = asyncio.create_task(_background_pdf_worker(paper_ids_map, papers))
        bg_task.add_done_callback(
            lambda t: logger.error(f"Background PDF worker crashed: {t.exception()}") 
            if t.exception() and not t.cancelled() else None
        )

    except Exception as e:
        error_message = str(e)
        logger.error(f"🚨 UNEXPECTED ERROR: {e}", exc_info=True)

    finally:
        db.close()
        progress.update(phase=ResearchPhase.COMPLETED)

    # 4. Return Fast Results (Abstracts Only initially)
    return {
        "success": error_message is None,
        "query": query,
        "task_id": task_id,
        "papers_found": len(saved_db_objects),
        "storage_failed": failed_storage,
        "embedding_failed": [], # Embeddings happen in bg now
        "db_ids": [obj.id for obj in saved_db_objects],
        "papers": [
            {
                "canonical_id": obj.canonical_id,
                "title": obj.title,
                "abstract": obj.abstract,
                "source": obj.paper_metadata.get("source", "unknown"),
                "pdf_status": obj.paper_metadata.get("pdf_status", "queued"),
                "year": obj.published_year,
                "authors": obj.paper_metadata.get("authors", []),
                "origin": obj.paper_metadata.get("origin")
            }
            for obj in saved_db_objects
        ],
        "error": error_message,
        "phases": progress.to_dict()
    }

async def _background_pdf_worker(paper_ids: Dict[int, str], papers_data: List[Dict]):
    """
    Background task to download PDFs, update DB, and generate embeddings.
    """
    logger.info(f"🚀 Starting background PDF download for {len(paper_ids)} papers...")
    
    db = SessionLocal()
    vector_client = get_client()
    
    try:
        # Match papers_data to DB IDs
        # papers_data acts as the source for URLs
        # We need to map properly. 
        # Actually, let's just use the DB objects since we saved metadata there?
        # But we need paper['pdf_url'] which might not be in DB yet if we only saved metadata.
        # Let's rely on papers_data matching order or map by canonical_id.
        
        # Create map: canonical_id -> paper_dict
        msg_map = {}
        for p in papers_data:
            cid = p.get("canonical_id")
            # Fallback ID logic from above
            if not cid:
                cid = build_canonical_id(p.get("id"), p.get("title", ""), p.get("source"))
            msg_map[cid] = p

        for db_id, canonical_id in paper_ids.items():
            paper_dict = msg_map.get(canonical_id)
            if not paper_dict:
                logger.warning(f"No paper_dict found for canonical_id={canonical_id}, db_id={db_id}. Skipping.")
                continue

            pdf_url = paper_dict.get("pdf_url")
            
            # Fetch fresh object
            db_obj = db.query(Paper).filter(Paper.id == db_id).first()
            if not db_obj: continue

            # Check if we should skip (Persistent Failure Tracking)
            meta = db_obj.paper_metadata or {}
            if meta.get("pdf_status") == "failed_permanent":
                logger.info(f"Skipping permanently failed PDF: {canonical_id}")
                continue
                
            attempts = meta.get("pdf_attempts", 0)
            if attempts > 3:
                meta["pdf_status"] = "failed_permanent"
                db_obj.paper_metadata = meta
                flag_modified(db_obj, "paper_metadata")
                db.commit()
                continue

            # Download
            if pdf_url and not db_obj.raw_text: # Only if text missing
                logger.info(f"⬇️ Downloading PDF for {db_id}: {pdf_url}")
                
                # Increment attempts
                meta["pdf_attempts"] = attempts + 1
                meta["pdf_status"] = "downloading"
                db_obj.paper_metadata = meta
                flag_modified(db_obj, "paper_metadata")
                db.commit()
                
                fulltext = await download_pdf(pdf_url)
                
                if is_nonempty_text(fulltext):
                    db_obj.raw_text = fulltext
                    meta["pdf_status"] = "success"
                    # Hash logic
                    content_hash = hashlib.md5(fulltext.encode()).hexdigest()
                    hashes = meta.get("pdf_hashes", [])
                    if content_hash not in hashes:
                        hashes.append(content_hash)
                        meta["pdf_hashes"] = hashes
                    
                    logger.info(f"✅ PDF Success for {db_id}")
                else:
                    meta["pdf_status"] = "failed_retry"
                    logger.warning(f"❌ PDF Failed for {db_id}")

                db_obj.paper_metadata = meta
                flag_modified(db_obj, "paper_metadata")
                db.commit()

            # Embed
            # Prefer abstract to keep vectors topic-focused. Fallback to truncated text.
            content_to_embed = db_obj.abstract
            if not is_nonempty_text(content_to_embed) and db_obj.raw_text:
                content_to_embed = db_obj.raw_text[:3000] # Truncate to avoid noise

            if is_nonempty_text(content_to_embed):
                chroma_id = f"paper-{db_obj.id}"
                try:
                    await asyncio.to_thread(
                         vector_client.store,
                         chroma_id,
                         content_to_embed[:8000], # Chunk limit
                         {"paper_db_id": db_obj.id, "canonical_id": db_obj.canonical_id}
                    )
                except Exception as ve:
                    # Log but continue to ensure other papers get processed
                    logger.error(f"⚠️ Embedding failed for {db_obj.canonical_id} (ID: {db_obj.id}): {ve}")

    except Exception as e:
        logger.error(f"Background worker failed: {e}", exc_info=True)
    finally:
        db.close()



async def ingest_local_file(
    file_bytes: bytes,
    filename: str,
    user_id: str
) -> Dict:
    """
    Ingests a local PDF file: extracts text, stores in DB, embeds in Chroma.
    """
    logger.info(f"📂 Ingesting local file: {filename}")
    db = SessionLocal()
    try:
        # 1. Extract Text
        text = await asyncio.to_thread(extract_text_from_pdf_bytes, file_bytes)
        if not is_nonempty_text(text):
            return {"success": False, "error": "Failed to extract text from PDF or empty file."}

        # 2. Generate Metadata
        # Use filename as title (remove extension)
        title = filename.rsplit(".", 1)[0].replace("_", " ").title()
        
        # Calculate Hash for Dedup
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # Canonical ID: "local_file:<hash>" to be robust
        canonical_id = f"local_file:{content_hash[:16]}"
        
        # 3. DB Upsert
        existing = db.query(Paper).filter(Paper.canonical_id == canonical_id).one_or_none()
        
        if existing:
            db_obj = existing
            # Update title if it looks like a better one? No, keep existing.
            logger.info(f"Local file dedup hit: {canonical_id}")
        else:
            db_obj = Paper(
                canonical_id=canonical_id,
                paper_id=f"local_{content_hash[:8]}", # Legacy ID
                title=title,
                abstract=text[:3000], # First 3000 chars as abstract fallback
                raw_text=text,
                published_year=2024, # Fallback
                paper_metadata={
                    "source": "local_file",
                    "user_uploaded": True,
                    "user_id": user_id,  # [REF] Using user_id for association
                    "filename": filename,
                    "authors": ["User Upload"],
                    "pdf_hashes": [hashlib.md5(text.encode()).hexdigest()]
                }
            )
            db.add(db_obj)
            
        db.commit()
        db.refresh(db_obj)
        
        # 4. Embed in Chroma
        vector_client = get_client()
        chroma_id = f"paper-{db_obj.id}"
        
        # Use extract_text_from_pdf_bytes result (full text)
        # But Chroma might have limits? We usually chunk or store summary.
        # Existing logic stores `db_obj.abstract`.
        # Here we stored first 3000 chars as abstract. That's fine for now.
        # Ideally we should chunk the full text, but RAG expects `db_obj.abstract` usually?
        # Let's align with `add_manual_paper`: store abstract.
        
        await asyncio.to_thread(
            vector_client.store,
            chroma_id,
            db_obj.abstract,
            {
                "paper_db_id": db_obj.id, 
                "canonical_id": db_obj.canonical_id,
                "source": "local_file",
                "user_uploaded": True,
                "user_id": user_id
            }
        )
        
        return {
            "success": True,
            "paper_id": db_obj.id,
            "canonical_id": db_obj.canonical_id,
            "title": db_obj.title,
            "source": "local_file"
        }

    except Exception as e:
        logger.error(f"Failed to ingest local file {filename}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        db.close()


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


async def get_relevant_context(
    query: str, 
    limit: int = 5, 
    max_tokens: int = 3000, 
    agent_name: str = "unknown"
) -> str:
    """
    Retrieves semantically relevant context from Chroma asynchronously.
    Enforces token budgets, deduplication, and provenance.
    """
    if not query:
        return ""

    # 1. Clean & Normalize
    clean_query = clean_text(query).lower()
    
    # 2. Retrieval with Async Wrapper and Error Handling
    client = get_client()
    if not client:
        logger.warning(f"RETRIEVAL: Agent={agent_name} - Client unavailable.")
        return ""

    try:
        results = await asyncio.to_thread(client.search, clean_query, n_results=limit)
    except Exception as e:
        logger.error(f"RETRIEVAL ERROR: Agent={agent_name} Query='{clean_query[:50]}...' Error={e}", exc_info=True)
        return ""
    
    # 2b. Fallback Strategy
    if not results and len(clean_query.split()) > 5:
        logger.info(f"RETRIEVAL_FALLBACK: '{clean_query[:50]}...' yielded 0. Retrying fallback.")
        fallback_query = " ".join(clean_query.split()[:5])
        try:
             results = await asyncio.to_thread(client.search, fallback_query, n_results=limit)
        except Exception as e:
             logger.error(f"RETRIEVAL FALLBACK FAILED: Agent={agent_name} Error={e}")
             results = []

    # 3. Log Retrieval Stats
    logger.info(f"RETRIEVAL: Agent={agent_name} Query='{clean_query[:50]}...' k={limit} Found={len(results)}")

    # 4. Filter & Format
    seen_ids = set()
    context_chunks = []
    current_tokens = 0
    
    for res in results:
        # Distance Threshold (approx 1.5 for cosine in Chroma is loose, but safe)
        # FIX 2: Note that hnsw:space=cosine implies distance = 1 - cosine_similarity.
        # Range is [0, 2]. 0 is identical, 1 is orthogonal, 2 is opposite.
        if res.get("distance", float('inf')) > 1.5:
             continue
             
        meta = res.get("metadata", {})
        pid = meta.get("canonical_id") or res.get("id")
        
        if pid in seen_ids:
            continue
        seen_ids.add(pid)
        
        text = res.get("document", "")
        if not text:
            continue
            
        # Provenance Header
        header = f"[Source: {pid}]"
        chunk = f"{header}\n{text}\n"
        
        # Token Check (FIX 3: Conservative estimate using 4.2 chars/token)
        chunk_tokens = int(len(chunk) / 4.2)
        if current_tokens + chunk_tokens > max_tokens:
            break
            
        context_chunks.append(chunk)
        current_tokens += chunk_tokens

    final_context = "\n".join(context_chunks)
    logger.info(f"RETRIEVAL_FINAL: TokenUsage={current_tokens} Chunks={len(context_chunks)}")
    
    return final_context
