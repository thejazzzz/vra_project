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

# ============================================================
#  OpenAI Client Singleton
# ============================================================

_client: Optional[OpenAI] = None
_client_lock = threading.Lock()


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise RuntimeError("OPENAI_API_KEY is missing")

                _client = OpenAI(api_key=api_key, timeout=30.0)

    return _client


ANALYSIS_MODEL = os.getenv(
    "OPENAI_ANALYSIS_MODEL",
    os.getenv("OPENAI_MODEL", "gpt-4o-mini")
)


# ============================================================
#  Normalization Helpers
# ============================================================

def _normalize_paper(p: Union[Paper, dict]) -> Dict[str, str]:
    """Normalize both dict-based and Pydantic papers."""

    if isinstance(p, dict):
        pid = p.get("canonical_id") or p.get("id") or p.get("paper_id") or ""
        title = p.get("title", "")
        summary = p.get("summary", "")
    else:
        # Pydantic Paper model only has id/title/summary
        pid = p.id
        title = p.title
        summary = p.summary

    return {
        "id": clean_text(pid),
        "title": clean_text(title),
        "summary": clean_text(summary),
    }


def _normalize_relation(r: dict) -> Optional[Dict[str, str]]:
    if not isinstance(r, dict):
        return None

    src = clean_text(r.get("source", ""))
    tgt = clean_text(r.get("target", ""))
    rel = clean_text(r.get("relation", "related_to"))

    if not (src and tgt):
        return None

    return {"source": src, "target": tgt, "relation": rel}


# ============================================================
#  Prompt Build
# ============================================================

def _build_context(query: str, papers: Optional[List[Union[Paper, dict]]], audience: str = "general") -> str:
    q = clean_text(query)

    # Audience instructions
    audience_instructions = {
        "phd": "Focus on methodology, technical depth, citation networks, and research gaps. Rigorous academic tone.",        "industry": "Focus on practical applications, market relevance, strategic value, and business trends. Executive summary tone.",
        "layman": "Explain concepts simply, avoid jargon, focus on the 'big picture' and real-world impact.",
        "general": "Provide a balanced academic summary suitable for general researchers."
    }
    instruction = audience_instructions.get(audience, audience_instructions["general"])

    prefix = f"AUDIENCE: {audience.upper()}\nINSTRUCTION: {instruction}\n\n"

    if not papers:
        return f"{prefix}User query only.\nQuery: {q}"

    items = []
    for p in papers[:5]:
        norm = _normalize_paper(p)
        if is_nonempty_text(norm["title"]) or is_nonempty_text(norm["summary"]):
            items.append(norm)

    if not items:
        return f"{prefix}No usable paper metadata.\nQuery: {q}"

    lines = [f"{prefix}User query: {q}", "", "Relevant papers:"]

    for idx, p in enumerate(items, 1):
        lines.extend([
            f"\nPaper {idx}:",
            f"ID: {p['id']}",
            f"Title: {p['title']}",
            f"Summary: {p['summary']}"
        ])

    return "\n".join(lines)


# ============================================================
#  Fallback
# ============================================================

def _safe_fallback(msg: str = "") -> Dict:
    return {"summary": msg or "Analysis failed.", "key_concepts": [], "relations": []}


# ============================================================
#  OpenAI Call
# ============================================================

def _call_openai_for_analysis(prompt: str) -> Dict:
    system_msg = (
        "You are an expert research analyst. Extract structured knowledge as JSON.\n"
        "Output MUST be:\n"
        "{\n"
        "  \"summary\": string,\n"
        "  \"key_concepts\": [string],\n"
        "  \"relations\": [ {\"source\": string, \"target\": string, \"relation\": \"related_to\"} ]\n"
        "}\n"
        "Rules:\n"
        "- Relations must reference conceptual terms only, not paper IDs.\n"
        "- No markdown, no extra fields."
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
            return _safe_fallback("Model returned no content.")

    except (APIError, APITimeoutError, RateLimitError) as e:
        logger.error(f"OpenAI API error: {e}")
        return _safe_fallback("OpenAI API error.")

    except Exception as e:
        logger.error(f"Unexpected OpenAI error: {e}", exc_info=True)
        return _safe_fallback("Unexpected OpenAI error.")

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.error("Model returned invalid JSON")
        return _safe_fallback("Invalid JSON.")


# ============================================================
#  Public Entrypoint
# ============================================================

async def run_analysis_task(
    query: str,
    papers: Optional[List[Union[Paper, dict]]] = None,
    audience: str = "general"
) -> Dict:

    prompt = _build_context(query, papers, audience)
    result = await asyncio.to_thread(_call_openai_for_analysis, prompt)

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
