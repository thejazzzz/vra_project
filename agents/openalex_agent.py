# agents/openalex_agent.py
import logging
from typing import Dict, List
from clients.openalex_client import openalex_client

logger = logging.getLogger(__name__)

class OpenAlexAgent:
    async def run(self, query: str, limit: int = 5) -> List[Dict]:
        logger.info(f"🔍 OpenAlexAgent → searching for '{query}'")
        results = await openalex_client.search_openalex(query, limit)
        normalized = []
        for paper in results:
            try:
                norm = self._normalize_paper(paper)
                normalized.append(norm)
            except Exception as e:
                logger.error(f"❌ Error normalizing OpenAlex paper '{paper.get('display_name')}': {e}")
        
        logger.info(f"📦 OpenAlexAgent → Normalized {len(normalized)}/{len(results)} papers.")
        return normalized

    async def get_by_ids(self, openalex_ids: List[str]) -> List[Dict]:
        logger.info(f"🔍 OpenAlexAgent → fetching {len(openalex_ids)} works")
        results = await openalex_client.get_openalex_by_ids(openalex_ids)
        normalized = []
        for paper in results:
            try:
                norm = self._normalize_paper(paper)
                normalized.append(norm)
            except Exception as e:
                logger.error(f"❌ Error normalizing OpenAlex paper ID '{paper.get('id')}': {e}")
        
        logger.info(f"📦 OpenAlexAgent → Normalized {len(normalized)}/{len(results)} batch papers.")
        return normalized

    def _normalize_paper(self, paper: Dict) -> Dict:
        """Convert OpenAlex work object to VRA VRAState paper format."""
        
        # Extract ID (e.g. https://openalex.org/W2741809807 -> W2741809807)
        raw_id = paper.get("id", "")
        openalex_id = raw_id.split("/")[-1] if raw_id else ""
        
        if not openalex_id:
            raise ValueError("Missing OpenAlex ID in work object")
        
        # Parse authors
        authors = []
        for authorship in paper.get("authorships", []):
            author = authorship.get("author", {})
            if author.get("display_name"):
                authors.append({
                    "authorId": author.get("id", "").split("/")[-1],
                    "name": author.get("display_name", "")
                })
            
        # Parse concepts
        concepts = []
        for concept in paper.get("concepts", []):
            if concept.get("display_name"):
                concepts.append(concept.get("display_name", ""))
            
        # Parse references
        references = []
        ref_works = paper.get("referenced_works", [])
        for ref_id in ref_works:
            references.append({"paperId": ref_id.split("/")[-1], "source": "openalex"})
            
        title = paper.get("display_name") or "Untitled Paper"
        summary = openalex_client.parse_abstract(paper.get("abstract_inverted_index"))
        
        logger.debug(f"📑 Normalized Paper: {title} ({openalex_id}) | Refs: {len(references)} | Concepts: {len(concepts)}")
            
        return {
            "id": openalex_id,
            "paper_id": openalex_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "published": paper.get("publication_date", ""),
            "url": paper.get("doi", "") or paper.get("id", ""),
            "source": "openalex",
            "metadata": {
                "citationCount": paper.get("cited_by_count", 0),
                "year": paper.get("publication_year"),
                "concepts": concepts,
                "references": references,
                "isOpenAccess": paper.get("open_access", {}).get("is_oa", False)
            }
        }

openalex_agent = OpenAlexAgent()
