# utils/sanitization.py
from typing import Optional
import re

CONTROL_CHARS = r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]"


def clean_text(value: Optional[str]) -> str:
    if value is None:
        return ""

    text = re.sub(CONTROL_CHARS, "", value)
    text = text.strip()

    # Optional: normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text


def is_nonempty_text(value: Optional[str]) -> bool:
    return bool(clean_text(value))
