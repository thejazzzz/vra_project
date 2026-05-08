# clients/openalex_client.py
import logging
import httpx
from typing import Dict, List, Optional
import os

logger = logging.getLogger(__name__)

class OpenAlexClient:
    def __init__(self):
        self.base_url = "https://api.openalex.org"
        self.email = os.getenv("OPENALEX_EMAIL", "admin@vra-project.local")
        self.headers = {"User-Agent": f"VRA-Project ({self.email})"}

    async def search_openalex(self, query: str, limit: int = 5) -> List[Dict]:
        """Search OpenAlex for works."""
        params = {
            "search": query,
            "per-page": limit,
            "mailto": self.email
        }
        url = f"{self.base_url}/works"
        
        logger.info(f"🚀 OpenAlex API → Searching for '{query}' (limit={limit})")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=self.headers, timeout=15.0)
                logger.debug(f"📊 OpenAlex Response: {response.status_code} for {url}")
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                logger.info(f"✅ OpenAlex returned {len(results)} search results.")
                return results
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ OpenAlex API Status Error: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"❌ OpenAlex search failed: {type(e).__name__}: {e}")
            return []

    async def get_openalex_by_ids(self, openalex_ids: List[str]) -> List[Dict]:
        """Fetch multiple works by OpenAlex IDs."""
        if not openalex_ids:
            return []
            
        # Extract just the ID part if full URLs are passed
        clean_ids = [id_str.split("/")[-1] for id_str in openalex_ids]
        id_filter = "|".join(clean_ids)
        
        params = {
            "filter": f"openalex:{id_filter}",
            "per-page": len(openalex_ids),
            "mailto": self.email
        }
        url = f"{self.base_url}/works"
        
        logger.info(f"📥 OpenAlex API → Batch fetching {len(clean_ids)} IDs")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=self.headers, timeout=20.0)
                logger.debug(f"📊 OpenAlex Batch Response: {response.status_code}")
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                logger.info(f"✅ OpenAlex retrieved {len(results)}/{len(clean_ids)} works by ID.")
                return results
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ OpenAlex Batch API Status Error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"❌ OpenAlex batch fetch failed: {type(e).__name__}: {e}")
            return []

    def parse_abstract(self, inverted_index: Optional[Dict[str, List[int]]]) -> str:
        """Parse OpenAlex abstract_inverted_index into text."""
        if not inverted_index:
            return ""
            
        words = []
        for word, positions in inverted_index.items():
            for pos in positions:
                words.append((pos, word))
                
        words.sort(key=lambda x: x[0])
        return " ".join([word for pos, word in words])

openalex_client = OpenAlexClient()
