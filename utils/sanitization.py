# File: utils/sanitization.py
from typing import Optional
import re

CONTROL_CHARS = r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]"


def clean_text(value: Optional[str]) -> str:
    """
    Normalize a text field:
    - Handle None safely
    - Strip ASCII control characters (preserves tab, line feed, and carriage return)
    - Strip leading/trailing whitespace
    """
    if value is None:
        return ""

    # Remove control characters (includes NULL \x00)
    text = re.sub(CONTROL_CHARS, "", value)

    # Strip whitespace
    return text.strip()

def is_nonempty_text(value: Optional[str]) -> bool:
    """
    True if, after cleaning, this is a non-empty string.
    """
    return bool(clean_text(value))
