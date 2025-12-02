# File: services/analysis_service.py
import asyncio
import json
import logging
import os
from typing import Dict, List, Optional

from openai import OpenAI, APIError, APITimeoutError, RateLimitError

from api.models.analysis_models import Paper

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


def _build_context(query: str, papers: Optional[List[Paper]]) -> str:
    """Formats context for LLM consumption."""
    if not papers:
        return f"User query only, no papers provided. Query: {query}"

    lines = [f"User query: {query}", "", "Relevant papers:"]

    for idx, paper in enumerate(papers[:5]):  # Limit to N papers in prompt
        # Support both dict-like and object-like paper representations
        if isinstance(paper, dict):
            title = (paper.get("title", "") or "").strip()
            summary = (paper.get("summary", "") or "").strip()
            pid = paper.get("id", "")
        else:
            title = (getattr(paper, "title", "") or "").strip()
            summary = (getattr(paper, "summary", "") or "").strip()
            pid = getattr(paper, "id", "")
        lines.append(f"\nPaper {idx + 1}:")
        lines.append(f"ID: {pid}")
        lines.append(f"Title: {title}")
        lines.append(f"Summary: {summary}")

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
        "summary": result.get("summary", ""),
        "key_concepts": result.get("key_concepts", []),
        "relations": result.get("relations", []),
    }
