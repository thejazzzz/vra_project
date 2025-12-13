# File: services/analysis_service.py
import asyncio
import json
import logging
import os
import threading
from typing import Dict, List, Optional, Union

from openai import OpenAI, APIError, APITimeoutError, RateLimitError

from api.models.analysis_models import Paper   # Pydantic Paper model (not DB model)
from utils.sanitization import clean_text, is_nonempty_text

logger = logging.getLogger(__name__)

# ============================================================
#  OpenAI Client (Thread-Safe Singleton)
# ============================================================

_client: Optional[OpenAI] = None
_client_lock = threading.Lock()


def _get_client() -> OpenAI:
    """
    Lazily initialize OpenAI client — thread safe.
    """
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise RuntimeError("OPENAI_API_KEY environment variable is NOT set!")

                _client = OpenAI(api_key=api_key, timeout=30.0)

    return _client


ANALYSIS_MODEL = os.getenv(
    "OPENAI_ANALYSIS_MODEL",
    os.getenv("OPENAI_MODEL", "gpt-4o-mini")
)

# ============================================================
#  NORMALIZATION HELPERS
# ============================================================

def _normalize_paper(paper: Union[Paper, dict]) -> Dict[str, str]:
    """
    Normalizes both ORM/Pydantic Paper objects and dict-based papers.
    Ensures consistent fields for LLM prompt building.
    """

    if isinstance(paper, dict):
        pid = (
            paper.get("canonical_id")
            or paper.get("id")
            or paper.get("paper_id")
            or ""
        )
        title = paper.get("title", "")
        summary = paper.get("summary", "")
    else:
        # Pydantic object (api/models/analysis_models.Paper)
        pid = getattr(paper, "canonical_id", "") or getattr(paper, "id", "")
        title = getattr(paper, "title", "")
        summary = getattr(paper, "summary", "")

    return {
        "id": clean_text(pid),
        "title": clean_text(title),
        "summary": clean_text(summary),
    }


def _normalize_relation(r: dict) -> Optional[Dict[str, str]]:
    """
    Ensures relation objects have valid sanitized fields.
    """
    if not isinstance(r, dict):
        return None

    normalized = {
        "source": clean_text(r.get("source", "")),
        "target": clean_text(r.get("target", "")),
        "relation": clean_text(r.get("relation", "related_to")),
    }

    if is_nonempty_text(normalized["source"]) and is_nonempty_text(normalized["target"]):
        return normalized

    return None


# ============================================================
#  LLM PROMPT CONTEXT BUILDER
# ============================================================

def _build_context(
    query: str,
    papers: Optional[List[Union[Paper, dict]]]
) -> str:
    """
    Builds structured prompt for global analysis.
    """
    clean_query = clean_text(query)

    if not papers:
        return f"User query only; no papers available.\nQuery: {clean_query}"

    lines: List[str] = [f"User query: {clean_query}", "", "Relevant papers:"]

    normalized: List[Dict[str, str]] = []
    for p in papers[:5]:  # limit context to keep prompt compact
        norm = _normalize_paper(p)
        if is_nonempty_text(norm["title"]) or is_nonempty_text(norm["summary"]):
            normalized.append(norm)

    if not normalized:
        return f"No valid paper metadata available.\nQuery: {clean_query}"

    for idx, paper in enumerate(normalized, start=1):
        lines.append(f"\nPaper {idx}:")
        lines.append(f"ID: {paper['id']}")
        lines.append(f"Title: {paper['title']}")
        lines.append(f"Summary: {paper['summary']}")

    return "\n".join(lines)


# ============================================================
#  SAFE FALLBACK
# ============================================================

def _safe_fallback(summary: str = "") -> Dict:
    """
    Returned when the OpenAI API misbehaves or returns invalid JSON.
    """
    return {
        "summary": summary or "Analysis could not be completed.",
        "key_concepts": [],
        "relations": [],
    }


# ============================================================
#  OPENAI CALL
# ============================================================

def _call_openai_for_analysis(prompt: str) -> Dict:
    """
    Calls OpenAI and ALWAYS returns valid JSON dict.
    """
    system_msg = (
        "You are an expert research analyst. Extract structured knowledge as JSON.\n"
        "Output MUST follow exactly:\n"
        "{\n"
        "  \"summary\": string,\n"
        "  \"key_concepts\": [string],\n"
        "  \"relations\": [ {\"source\": string, \"target\": string, \"relation\": \"related_to\"} ]\n"
        "}\n"
        "Rules:\n"
        "- Relations must reference conceptual terms ONLY.\n"
        "- Do NOT reference paper IDs.\n"
        "- No markdown. No extra fields."
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
            logger.warning("⚠️ OpenAI returned empty content.")
            return _safe_fallback("No analysis output.")

    except (APIError, APITimeoutError, RateLimitError) as e:
        logger.error(f"OpenAI API failure: {e}", exc_info=True)
        return _safe_fallback("OpenAI API error occurred.")

    except Exception as e:
        logger.error(f"Unexpected OpenAI error: {e}", exc_info=True)
        return _safe_fallback("Unexpected model error.")

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.error("Invalid JSON returned by model", exc_info=True)
        return _safe_fallback(content)


# ============================================================
#  PUBLIC ENTRYPOINT
# ============================================================

async def run_analysis_task(
    query: str,
    papers: Optional[List[Union[Paper, dict]]] = None
) -> Dict:
    """
    Global analysis stage of the workflow.
    Converts papers into structured conceptual knowledge.
    """
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
