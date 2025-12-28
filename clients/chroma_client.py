# File: clients/chroma_client.py

"""
Modern, migration-safe Chroma client factory.
Prefers remote HTTP client when CHROMA_SERVER is set.
Defaults to local PersistentClient.
"""

import os
import logging
import threading
import urllib.parse
from typing import Optional, Any, Dict

try:
    from chromadb import PersistentClient, HttpClient
except Exception:
    raise RuntimeError("Chromadb >=0.5.0 is required. Run: pip install chromadb --upgrade")

logger = logging.getLogger(__name__)


class _ChromaClient:
    def __init__(self):
        server = os.getenv("CHROMA_SERVER", "").strip()
        self._client = None

        # -----------------------
        # 1️⃣ Remote deployment (HTTP mode)
        # -----------------------
        if server:
            parsed = urllib.parse.urlparse(server)
            host = parsed.hostname
            port = parsed.port or (80 if parsed.scheme == "http" else 443)

            try:
                logger.info(f"Connecting to remote Chroma at: {host}:{port}")
                self._client = HttpClient(host=host, port=port, ssl=(parsed.scheme == "https"))
            except Exception as e:
                logger.error(f"Failed HTTP Chroma client: {e}", exc_info=True)

        # -----------------------
        # 2️⃣ Local persistent DB (DuckDB+Parquet)
        # -----------------------
        if self._client is None:
            try:
                logger.info("Initializing local persistent Chroma client...")
                self._client = PersistentClient(path="./chroma_storage")
            except Exception as e:
                logger.critical("FATAL: Cannot initialize Chroma client.", exc_info=True)
                raise

        # -----------------------
        # 3️⃣ Create or load collection
        # -----------------------
        try:
            self._collection = self._client.get_or_create_collection(
                name="vra_data",
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            logger.critical("FATAL: Cannot create or load collection.", exc_info=True)
            raise

    # ============================================================
    # Public API — store + search
    # ============================================================

    def store(self, key: str, value: Any, metadata: Optional[Dict] = None):
        try:
            self._collection.add(
                ids=[key],
                documents=[str(value)],
                metadatas=[metadata] if metadata else None
            )
        except Exception as e:
            logger.error(f"Failed store, trying upsert. Error: {e}", exc_info=True)
            self._collection.upsert(
                ids=[key],
                documents=[str(value)],
                metadatas=[metadata] if metadata else None
            )

    def search(self, query: str, n_results: int = 5) -> list[Dict[str, Any]]:
        try:
            # We request documents, metadatas, and distances
            result = self._collection.query(
                query_texts=[query], 
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            # The result is a dict of lists (batch queries). We only sent one query.
            # result['ids'][0] -> list of IDs
            # result['documents'][0] -> list of docs
            
            ids = result.get("ids", [[]])[0]
            docs = result.get("documents", [[]])[0]
            metas = result.get("metadatas", [[]])[0]
            dists = result.get("distances", [[]])[0]

            structured_results = []
            for i in range(len(ids)):
                structured_results.append({
                    "id": ids[i],
                    "document": docs[i],
                    "metadata": metas[i] if metas else {},
                    "distance": dists[i] if dists else 0.0
                })
            
            # FIX 1: Explicitly SORT by distance (ascending for cosine distance)
            structured_results.sort(key=lambda x: x["distance"])
                
            return structured_results

        except Exception as e:
            logger.error(f"Chroma query failed: {e}", exc_info=True)
            return []


# -----------------------
# Singleton accessor
# -----------------------
_client: Optional[_ChromaClient] = None
_client_lock = threading.Lock()


def get_client() -> _ChromaClient:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = _ChromaClient()
    return _client
