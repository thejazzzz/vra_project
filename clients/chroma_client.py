"""
Dynamic, version-safe Chroma client factory.
Prefers remote HTTP client when CHROMA_SERVER is set.
Falls back to local DuckDB+Parquet persistence.
"""

import os
import logging
import threading
import urllib.parse
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

        # Validate URL if provided
        if server:
            parsed = urllib.parse.urlparse(server)
            if parsed.scheme not in ("http", "https"):
                raise ValueError("CHROMA_SERVER must be a valid http(s) URL")
            if parsed.scheme == "http":
                logging.warning("CHROMA_SERVER is using insecure scheme http; consider using https")

        self._client = None

        # -----------------------
        # 1️⃣ HTTP Client if CHROMA_SERVER is set
        # -----------------------
        if server:
            HttpClient = getattr(chromadb, "HttpClient", None)

            # older import structure fallback
            if HttpClient is None:
                http_mod = getattr(chromadb, "http", None)
                HttpClient = getattr(http_mod, "HttpClient", None) if http_mod else None

            if HttpClient:
                parsed = urllib.parse.urlparse(server)
                host = parsed.hostname
                port = parsed.port or (80 if parsed.scheme == "http" else 443)

                try:
                    self._client = HttpClient(
                        host=host,
                        port=port,
                        ssl=(parsed.scheme == "https")
                    )
                except Exception as e:
                    logging.error(f"HttpClient init failed: {e}", exc_info=True)

            # If HTTP init failed → fallback to Settings
            if self._client is None:
                try:
                    if Settings:
                        self._client = chromadb.Client(Settings(chroma_server=server))
                    else:
                        self._client = chromadb.Client()
                except Exception as e:
                    logging.error(f"Settings-based client init failed: {e}", exc_info=True)

        # -----------------------
        # 2️⃣ Local Client fallback
        # -----------------------
        if self._client is None:
            try:
                if Settings:
                    self._client = chromadb.Client(
                        Settings(
                            chroma_db_impl="duckdb+parquet",
                            persist_directory="./chroma/"
                        )
                    )
                else:
                    self._client = chromadb.Client()
            except Exception as e:
                logging.error("Failed to initialize any Chroma client", exc_info=True)
                raise

        # -----------------------
        # 3️⃣ Create / get collection
        # -----------------------
        try:
            self._collection = self._client.get_or_create_collection("vra_data")
        except Exception:
            self._collection = self._client.create_collection("vra_data")

    # ============================================================
    # Public API — store + search
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
            self._collection.upsert(
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
