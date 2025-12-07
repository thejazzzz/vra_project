# File: services/analysis_service.py
import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Union

from openai import OpenAI, APIError, APITimeoutError, RateLimitError

from api.models.analysis_models import Paper
from utils.sanitization import clean_text, is_nonempty_text

logger = logging.getLogger(__name__)

# Lazily initialized OpenAI client
_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """Lazily initialize the OpenAI client."""
    global _client
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
    """
    Normalize a paper object (Pydantic or dict) into a clean dict with
    id, title, summary, all sanitized.
    """
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


def _build_context(query: str, papers: Optional[List[Paper]]) -> str:
    """Formats context for LLM consumption (sanitized)."""
    clean_query = clean_text(query)

    if not papers:
        return f"User query only, no papers provided. Query: {clean_query}"

    lines: List[str] = [f"User query: {clean_query}", "", "Relevant papers:"]

    # Normalize & filter papers
    normalized: List[Dict[str, str]] = []
    for p in papers[:5]:  # Limit to N papers in prompt
        norm = _normalize_paper(p)
        # Keep only if at least title or summary has real content
        if not (is_nonempty_text(norm["title"]) or is_nonempty_text(norm["summary"])):
            continue
        normalized.append(norm)

    if not normalized:
        return f"User query only, no usable paper metadata. Query: {clean_query}"

    for idx, paper in enumerate(normalized, start=1):
        lines.append(f"\nPaper {idx}:")
        lines.append(f"ID: {paper['id']}")
        lines.append(f"Title: {paper['title']}")
        lines.append(f"Summary: {paper['summary']}")

    return "\n".join(lines)


def _safe_fallback(summary: str = "") -> Dict:
    """Fallback structure guaranteeing a valid AnalysisResult."""
    return {
        "summary": summary or "Analysis could not be completed.",
        "key_concepts": [],
        "relations": [],
    }


def _call_openai_for_analysis(prompt: str) -> Dict:
    """
    Performs structured analysis via OpenAI.
    Always returns a dict with keys: summary, key_concepts, relations
    """
    system_msg = (
        "You are an expert research analyst. "
        "Extract structured knowledge as JSON. "
        "Important: Format relations ONLY using this schema:\n"
        "{\n"
        "  \"summary\": string,\n"
        "  \"key_concepts\": [string],\n"
        "  \"relations\": [\n"
        "    {\"source\": string, \"target\": string, \"relation\": \"related_to\"}\n"
        "  ]\n"
        "}\n"
        "Relations must describe conceptual relationships between key concepts only. "
        "Do NOT reference paper IDs in relations. "
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
        if not resp.choices:
            logger.warning("OpenAI returned empty choices list")
            return _safe_fallback("Analysis returned no results.")
        content = resp.choices[0].message.content
    except (APIError, APITimeoutError, RateLimitError) as e:
        logger.error(f"OpenAI API failed: {e}", exc_info=True)
        return _safe_fallback("Analysis failed due to OpenAI API error.")
    except Exception as e:
        logger.error(f"Unexpected error during OpenAI call: {e}", exc_info=True)
        return _safe_fallback("Unexpected analysis error occurred.")

    # Parse JSON safely
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in OpenAI response: {e}", exc_info=True)
        return _safe_fallback(content)


async def run_analysis_task(query: str, papers: Optional[List[Paper]] = None) -> Dict:
    """
    Executes structured multi-document analysis asynchronously.
    """
    context = _build_context(query, papers)

    result = await asyncio.to_thread(_call_openai_for_analysis, context)

    # Final safeguard for malformed response
    return {
        "summary": clean_text(result.get("summary", "")),
        "key_concepts": [
            clean_text(c) for c in result.get("key_concepts", []) if is_nonempty_text(c)
        ],
        "relations": [
            r for r in result.get("relations", [])
            if isinstance(r, dict)
            and is_nonempty_text(r.get("source"))
            and is_nonempty_text(r.get("target"))
        ],
    }
