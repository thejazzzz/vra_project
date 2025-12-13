# utils/id_normalization.py
from typing import Optional
import hashlib


def normalize_arxiv_id(raw_id: str) -> Optional[str]:
    if not raw_id or not raw_id.strip():
        return None
    return raw_id.strip().split("/")[-1]


def to_canonical_id(source: str, identifier: str) -> Optional[str]:
    """
    Builds universal canonical ID.
    """
    if not source or not identifier:
        return None

    source = source.lower().strip()
    identifier = identifier.strip()

    if not source or not identifier:
        return None

    # ---- Known sources ----
    if source == "arxiv":
        clean_id = normalize_arxiv_id(identifier)
        return f"arxiv:{clean_id}" if clean_id else None

    if source in ("semantic_scholar", "s2"):
        return f"s2:{identifier}"

    if source in ("pubmed", "pmid"):
        return f"pmid:{identifier}"

    if source in ("ieee", "ieee_xplore"):
        return f"ieee:{identifier}"

    if source in ("google_scholar", "gs"):
        return f"gs:{identifier}"

    # ---- fallback ----
    return f"{source}:{identifier}"

def build_canonical_id(primary_id: Optional[str], title: Optional[str], source: Optional[str]) -> str:
    """
    Deterministic fallback canonical ID using:
    - source
    - primary ID if available
    - otherwise: sha1(title)
    """

    # Prefer primary identifier
    if source and primary_id:
        cid = to_canonical_id(source, primary_id)
        if cid:
            return cid

    # Title-based fallback
    clean_title = (title or "").lower().strip()
    h = hashlib.sha1(clean_title.encode("utf-8")).hexdigest()[:16]

    src = source.lower().strip() if source else "unknown"
    return f"{src}:{h}"

