# File: services/analysis_service.py
import asyncio
import json
import logging
import os
from typing import Dict, List, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI()
ANALYSIS_MODEL = os.getenv("OPENAI_ANALYSIS_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))


def _build_context(query: str, papers: Optional[List[Dict]]) -> str:
    """Builds a text context from the given papers for the LLM."""
    if not papers:
        return f"User query only, no papers provided. Query: {query}"

    lines = [f"User query: {query}", "", "Relevant papers:"]

    for idx, paper in enumerate(papers[:5]):  # limit to first N to keep prompt manageable
        title = paper.get("title", "").strip()
        summary = paper.get("summary", "").strip()
        pid = paper.get("id", "")
        lines.append(f"\nPaper {idx + 1}:")
        lines.append(f"ID: {pid}")
        lines.append(f"Title: {title}")
        lines.append(f"Abstract: {summary}")

    return "\n".join(lines)


def _call_openai_for_analysis(prompt: str) -> Dict:
    """
    Calls OpenAI to perform:
      - summary
      - key_concepts
      - relations (knowledge graph style)
    Returns a dict parsed from JSON.
    """
    system_msg = (
        "You are an expert research analyst. "
        "Given a user query and a set of papers (titles and abstracts), "
        "you must analyze them and respond STRICTLY as a JSON object with this schema:\n"
        "{\n"
        '  \"summary\": string,                    // high level summary\n'
        '  \"key_concepts\": [string, ...],       // important terms/topics\n'
        '  \"relations\": [                       // knowledge graph edges\n'
        "    {\"source\": string, \"target\": string, \"relation\": string}\n"
        "  ]\n"
        "}\n"
        "Do not include any extra keys. Do not wrap in markdown. "
        "Use concise but informative text."
    )

    resp = client.chat.completions.create(
        model=ANALYSIS_MODEL,
        temperature=0,
        response_format={  # force JSON object
            "type": "json_object"
        },
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
    )

    content = resp.choices[0].message.content
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON from OpenAI response", exc_info=True)
        # fallback minimal shape
        return {
            "summary": content or "",
            "key_concepts": [],
            "relations": [],
        }


async def run_analysis_task(query: str, papers: Optional[List[Dict]] = None) -> Dict:
    """
    Orchestrates building context and calling OpenAI in a non-blocking way.
    Returns a dict matching AnalysisResult schema.
    """
    context = _build_context(query, papers)

    # Offload blocking HTTP call to thread
    result = await asyncio.to_thread(_call_openai_for_analysis, context)

    # Ensure all required keys exist
    summary = result.get("summary", "")
    key_concepts = result.get("key_concepts", [])
    relations = result.get("relations", [])

    if not isinstance(key_concepts, list):
        key_concepts = []

    if not isinstance(relations, list):
        relations = []

    return {
        "summary": summary,
        "key_concepts": key_concepts,
        "relations": relations,
    }
