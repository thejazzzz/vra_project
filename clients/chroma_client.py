"""
Dynamic, version-safe Chroma client factory.
Prefers remote HTTP client when CHROMA_SERVER is set.
Falls back to local DuckDB+Parquet persistence.
"""

import os
from typing import Optional, Any, Dict

# dynamic import to avoid IDE errors and API changes
try:
    import chromadb
    from chromadb.config import Settings
except Exception:
    chromadb = None
    Settings = None


class _ChromaClient:
    def __init__(self):
        if chromadb is None:
            raise RuntimeError("chromadb package is missing. Install with `pip install chromadb`.")

        server = os.getenv("CHROMA_SERVER", "").strip()

        # -----------------------
        # 1. HTTP Client (if CHROMA_SERVER is set)
        # -----------------------
        if server:
            HttpClient = getattr(chromadb, "HttpClient", None)

            # alternative import path (older versions)
            if HttpClient is None:
                http_mod = getattr(chromadb, "http", None)
                HttpClient = getattr(http_mod, "HttpClient", None) if http_mod else None

            if HttpClient:
                self._client = HttpClient(host=server)
            else:
                # fallback: use Client(Settings)
                if Settings:
                    try:
                        self._client = chromadb.Client(Settings(chroma_server=server))
                    except Exception:
                        self._client = chromadb.Client(Settings())
                else:
                    self._client = chromadb.Client()

        # -----------------------
        # 2. Local Client (default)
        # -----------------------
        else:
            if Settings:
                self._client = chromadb.Client(
                    Settings(
                        chroma_db_impl="duckdb+parquet",
                        persist_directory="./chroma/"
                    )
                )
            else:
                self._client = chromadb.Client()

        # -----------------------
        # 3. Collection creation
        # -----------------------
        try:
            self._collection = self._client.get_or_create_collection("vra_data")
        except Exception:
            self._collection = self._client.create_collection("vra_data")

    # ============================================================
    # Public API: store + search
    # ============================================================

    def store(self, key: str, value: Any, metadata: Optional[Dict] = None):
        """Store a document by id."""
        try:
            self._collection.add(
                ids=[key],
                documents=[str(value)],
                metadatas=[metadata] if metadata else None
            )
        except Exception:
            # fallback for upsert-style behavior
            self._collection.add(
                ids=[key],
                documents=[str(value)],
                metadatas=[metadata] if metadata else None
            )

    def search(self, query: str, n_results: int = 5):
        """Query by text and return a plain list of documents."""
        try:
            result = self._collection.query(
                query_texts=[query],
                n_results=n_results
            )
            docs = result.get("documents") if isinstance(result, dict) else None
            return docs[0] if docs else []
        except Exception:
            return []


# -----------------------
# Singleton-style accessor
# -----------------------
_client: Optional[_ChromaClient] = None


def get_client() -> _ChromaClient:
    global _client
    if _client is None:
        _client = _ChromaClient()
    return _client
