import pytest
from services.reporting.export_service import ExportService

def test_sanitize_mixed_content():
    content = "Use List<String> inside <div> container"
    sanitized = ExportService.sanitize_markdown(content)
    assert sanitized == content, f"Expected {content}, got {sanitized}"

def test_sanitize_sneaky_script():
    content = "<script>alert('hack')</script>"
    sanitized = ExportService.sanitize_markdown(content)
    assert "script" not in sanitized
    assert "alert('hack')" in sanitized

def test_sanitize_broken_html():
    content = "<div><span>test"
    sanitized = ExportService.sanitize_markdown(content)
    assert sanitized == content, f"Expected {content}, got {sanitized}"

def test_sanitize_capitalized_tags():
    content = "<IFRAME src='evil.com'></IFRAME>"
    sanitized = ExportService.sanitize_markdown(content)
    assert "IFRAME" not in sanitized
    assert "iframe" not in sanitized.lower()

def test_sanitize_none():
    sanitized = ExportService.sanitize_markdown(None)
    assert sanitized == ""
