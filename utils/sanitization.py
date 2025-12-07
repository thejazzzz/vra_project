# File: utils/sanitization.py
from typing import Optional


def clean_text(value: Optional[str]) -> str:
    """
    Normalize a text field:
    - Handle None safely
    - Strip NULL/control chars
    - Strip leading/trailing whitespace
    """
    if value is None:
        return ""
    # Remove common NULL chars
    text = value.replace("\x00", "").replace("\u0000", "")
    # Strip whitespace
    text = text.strip()
    return text


def is_nonempty_text(value: Optional[str]) -> bool:
    """
    True if, after cleaning, this is a non-empty string.
    """
    return bool(clean_text(value))
