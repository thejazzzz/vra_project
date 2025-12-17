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
    os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
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

    evidence_raw = r.get("evidence", {})
    evidence: Dict[str, str] = {}

    if isinstance(evidence_raw, dict):
        if "paper_id" in evidence_raw:
            evidence["paper_id"] = clean_text(evidence_raw.get("paper_id", ""))
        if "excerpt" in evidence_raw:
            evidence["excerpt"] = clean_text(evidence_raw.get("excerpt", ""))

    if not (src and tgt):
        return None

    return {
        "source": src,
        "target": tgt,
        "relation": rel,
        "evidence": evidence,
    }

# ============================================================
#  Prompt Builder
# ============================================================

def _build_context(
    query: str,
    papers: Optional[List[Union[Paper, dict]]],
    audience: str = "general",
) -> str:
    q = clean_text(query)

    audience_instructions = {
        "general": "Provide a clear, concise research-oriented analysis.",
        "phd": "Focus on methodology, technical depth, citation networks, and research gaps.",
        "industry": "Focus on practical applications, market relevance, and strategic value.",
    }

    instruction = audience_instructions.get(
        audience.lower(),
        audience_instructions["general"],
    )

    relation_types = """
    Relation types:
    - uses: A uses B
    - extends: A builds upon B
    - improves: A improves B
    - related_to: Generic connection
    """

    prefix = (
        f"AUDIENCE: {audience.upper()}\n"
        f"INSTRUCTION: {instruction}\n"
        f"{relation_types}\n"
    )

    if not papers:
        return f"{prefix}User query only.\nQuery: {q}"

    items: List[Dict[str, str]] = []

    for p in papers[:5]:
        norm = _normalize_paper(p)
        if is_nonempty_text(norm["title"]) or is_nonempty_text(norm["summary"]):
            items.append(norm)

    if not items:
        return f"{prefix}No usable paper metadata.\nQuery: {q}"

    lines = [f"{prefix}User query: {q}", "", "Relevant papers:"]

    for idx, p in enumerate(items, 1):
        lines.extend(
            [
                f"\nPaper {idx}:",
                f"ID: {p['id']}",
                f"Title: {p['title']}",
                f"Summary: {p['summary']}",
            ]
        )

    return "\n".join(lines)

# ============================================================
#  Fallback
# ============================================================

def _safe_fallback(msg: str = "") -> Dict:
    return {
        "summary": msg or "Analysis failed.",
        "nodes": [],
        "key_concepts": [],
        "relations": [],
    }

# ============================================================
#  OpenAI Call
# ============================================================

def _call_openai_for_analysis(prompt: str) -> Dict:
    system_msg = (
        "You are an expert research analyst. Extract structured knowledge as JSON.\n"
        "Output MUST be:\n"
        "{\n"
        "  \"summary\": string,\n"
        "  \"nodes\": [{\"id\": string, \"type\": \"concept|method|metric|task|tool\"}],\n"
        "  \"relations\": [{\"source\": string, \"target\": string, "
        "\"relation\": \"uses|extends|improves|related_to\", "
        "\"evidence\": {\"paper_id\": string, \"excerpt\": string}}]\n"
        "}\n"
        "Rules:\n"
        "- Nodes must be extracted entities.\n"
        "- Relations must link two existing node IDs.\n"
        "- No markdown."
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

    except (APIError, APITimeoutError, RateLimitError) as exc:
        logger.error("OpenAI API error: %s", exc)
        return _safe_fallback("OpenAI API error.")

    except Exception as exc:
        logger.error("Unexpected OpenAI error", exc_info=True)
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
    audience: str = "general",
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


def generate_report_content(prompt: str) -> str:
    """
    Generate a markdown report based on the provided prompt using the LLM.
    This is a wrapper around the OpenAI client.
    """
    system_msg = "You are a research assistant writing a formal report. Use Markdown."
    
    try:
        # We run this synchronously in a thread because OpenAI client is sync
        # But wait, the caller might differ. ReportingAgent calls it synchronously? 
        # ReportingAgent.py: report_text = generate_report_content(prompt)
        # It seems ReportingAgent expects a synchronous call or it's running in sync ctx.
        # Let's check ReportingAgent.run. It is a sync method: def run(self, state): ...
        # So this should be synchronous.
        
        resp = _get_client().chat.completions.create(
            model=ANALYSIS_MODEL,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
        )
        content = resp.choices[0].message.content if resp.choices else ""
        return content or "Report generation returned empty."

    except Exception as exc:
        logger.error("Report generation failed: %s", exc)
        return "Error communicating with LLM. Please check logs for details."