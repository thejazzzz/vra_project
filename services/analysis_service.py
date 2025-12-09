# File: services/analysis_service.py
import asyncio
import json
import logging
import os
import threading
from typing import Dict, List, Optional, Union

from openai import OpenAI, APIError, APITimeoutError, RateLimitError

from api.models.analysis_models import Paper
from utils.sanitization import clean_text, is_nonempty_text

logger = logging.getLogger(__name__)

# Lazily initialized OpenAI client with thread-safe initialization
_client: Optional[OpenAI] = None
_client_lock = threading.Lock()


def _get_client() -> OpenAI:
    """Lazily initialize the OpenAI client (thread-safe)."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
                _client = OpenAI(api_key=api_key, timeout=30.0)
    return _client


ANALYSIS_MODEL = os.getenv(
    "OPENAI_ANALYSIS_MODEL",
    os.getenv("OPENAI_MODEL", "gpt-4o-mini")
)


def _normalize_paper(paper: Union[Paper, dict]) -> Dict[str, str]:
    """Convert input object into a safe normalized paper representation."""
    if isinstance(paper, dict):
        pid = paper.get("id", "")
        title = paper.get("title", "")
        summary = paper.get("summary", "")
    else:
        pid = getattr(paper, "id", "")
        title = getattr(paper, "title", "")
        summary = getattr(paper, "summary", "")

    return {
        "id": clean_text(pid),
        "title": clean_text(title),
        "summary": clean_text(summary),
    }


def _normalize_relation(r: dict) -> Optional[Dict[str, str]]:
    """Normalize and validate a relation dict."""
    if not isinstance(r, dict):
        return None

    normalized = {
        "source": clean_text(r.get("source", "")),
        "target": clean_text(r.get("target", "")),
        "relation": clean_text(r.get("relation", "related_to"))
    }

    if is_nonempty_text(normalized["source"]) and is_nonempty_text(normalized["target"]):
        return normalized

    return None


def _build_context(query: str, papers: Optional[List[Paper]]) -> str:
    """Build LLM prompt using query + truncated sanitized paper metadata."""
    clean_query = clean_text(query)

    if not papers:
        return f"User query only; no papers provided.\nQuery: {clean_query}"

    lines: List[str] = [f"User query: {clean_query}", "", "Relevant papers:"]

    normalized: List[Dict[str, str]] = []
    for p in papers[:5]:
        norm = _normalize_paper(p)
        if is_nonempty_text(norm["title"]) or is_nonempty_text(norm["summary"]):
            normalized.append(norm)

    if not normalized:
        return f"User query only; no usable paper metadata.\nQuery: {clean_query}"

    for idx, paper in enumerate(normalized, start=1):
        lines.append(f"\nPaper {idx}:")
        lines.append(f"ID: {paper['id']}")
        lines.append(f"Title: {paper['title']}")
        lines.append(f"Summary: {paper['summary']}")

    return "\n".join(lines)


def _safe_fallback(summary: str = "") -> Dict:
    """Fallback result structure on error or malformed model output."""
    return {
        "summary": summary or "Analysis could not be completed.",
        "key_concepts": [],
        "relations": [],
    }


def _call_openai_for_analysis(prompt: str) -> Dict:
    """
    Performs structured analysis via OpenAI.
    Always returns a JSON-safe dict with required keys.
    """
    system_msg = (
        "You are an expert research analyst. "
        "Extract structured knowledge as JSON. "
        "Important: Format relations ONLY using this schema:\n"
        "{"
        "\"summary\": string,"
        "\"key_concepts\": [string],"
        "\"relations\": ["
        "{\"source\": string, \"target\": string, \"relation\": \"related_to\"}"
        "]"
        "}"
        "Relations must be between conceptual terms ONLY. "
        "Do NOT reference paper IDs. "
        "No markdown, no extra fields."
    )

    try:
        resp = _get_client().chat.completions.create(
            model=ANALYSIS_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
        )
        content = resp.choices[0].message.content if resp.choices else None

        if not content:
            logger.warning("OpenAI returned empty message content")
            return _safe_fallback("No analysis output received.")

    except (APIError, APITimeoutError, RateLimitError) as e:
        logger.error(f"OpenAI API failed: {e}", exc_info=True)
        return _safe_fallback("Analysis failed due to OpenAI API timeout/api issue.")

    except Exception as e:
        logger.error(f"Unexpected error during OpenAI call: {e}", exc_info=True)
        return _safe_fallback("Unexpected error occurred during analysis.")

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.error("Invalid JSON returned by model", exc_info=True)
        return _safe_fallback(content)


async def run_analysis_task(query: str, papers: Optional[List[Paper]] = None) -> Dict:
    """Asynchronously run global document analysis and post-normalize result."""
    context = _build_context(query, papers)
    result = await asyncio.to_thread(_call_openai_for_analysis, context)

    return {
        "summary": clean_text(result.get("summary", "")),
        "key_concepts": [
            clean_text(c)
            for c in result.get("key_concepts", [])
            if is_nonempty_text(clean_text(c))
        ],
        "relations": [
            norm
            for r in result.get("relations", [])
            if (norm := _normalize_relation(r)) is not None
        ],
    }
