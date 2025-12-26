#File: services/data_normalization_service.py
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def normalize_date(date_str: Any) -> Optional[int]:
    """
    Extracts a 4-digit year from various date formats.
    Supports: YYYY, YYYY-MM-DD, ISO Strings.
    Returns: Year as Integer or None.
    """
    if not date_str:
        return None
        
    date_str = str(date_str).strip()
    
    # 1. Exact 4-digit year
    if re.match(r"^\d{4}$", date_str):
        return int(date_str)
        
    # 2. ISO / standard date starting with YYYY
    match = re.search(r"(\d{4})-\d{2}-\d{2}", date_str)
    if match:
        return int(match.group(1))

    # 3. Try standard datetime parsing
    try:
        # Arxiv often returns '2023-10-15T12:00:00Z'
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.year
    except ValueError:
        pass
        
    # 4. Fallback regex for any 4 digits (use with caution)
    # Only if it looks like a year in a valid range (1900 - 2100)
    # And preferably surrounded by boundaries or non-digit chars
    matches = re.findall(r"\b(19|20)\d{2}\b", date_str)
    if matches:
        # Return the first valid year found
        return int(matches[0])
        
    return None

def normalize_authors(authors: Any) -> List[str]:
    """
    Standardizes author list to simple list of strings.
    Handles: strings, list of strings, list of dicts.
    """
    normalized = []
    
    if not authors:
        return []
        
    if isinstance(authors, str):
        # Handle comma-separated list of authors
        return [a.strip() for a in authors.split(",") if a.strip()]
        
    if isinstance(authors, list):
        for a in authors:
            if isinstance(a, str):
                normalized.append(a.strip())
            elif isinstance(a, dict):
                # Common pattern: {'name': '...'}
                name = a.get("name")
                if name:
                    normalized.append(name.strip())
                    
    return normalized

def normalize_references(references: Any) -> List[Dict[str, Any]]:
    """
    Standardizes references list.
    Ensures keys: 'id', 'title', 'url' (optional), 'year' (optional).
    """
    if not references or not isinstance(references, list):
        return []

    normalized = []
    for ref in references:
        if isinstance(ref, dict):
            # Normalize keys and types
            clean_ref = {
                "id": str(ref.get("id", "")).strip(),
                "title": str(ref.get("title", "")).strip(),
                "url": str(ref.get("url", "")).strip(),
                "year": normalize_date(ref.get("year"))
            }
            # Only keep references with at least a title or id
            if clean_ref["id"] or clean_ref["title"]:
                normalized.append(clean_ref)
                
    return normalized
