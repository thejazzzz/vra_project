# services/reporting/export_service.py
from typing import Dict, Any, List, Optional, Union
import logging
import os
import re

logger = logging.getLogger(__name__)

class ExportService:
    """
    Handles conversion of Markdown reports to PDF, DOCX, etc.
    Ensures canonical output formatting.
    """

    @staticmethod
    def export_report(state: Dict[str, Any], format: str) -> bytes:
        """
        Exports the report to the requested format using ReportFormatter.
        
        Args:
            state: The full report state dictionary.
            format: Target format ('pdf', 'docx', 'markdown', 'latex').

        Returns:
            bytes: The binary content of the exported report.
        """
        from services.formatter.formatter_core import ReportFormatter
        try:
            return ReportFormatter.format_report(state, export_format=format)
        except Exception as e:
            logger.error(f"Export failed for format {format}: {e}")
            raise 

    @staticmethod
    def sanitize_markdown(content: str) -> str:
        """
        Sanitizes markdown content by stripping dangerously scriptable or layout-breaking HTML tags.
        Allows safe HTML (div, span) and generic types (List<String>).
        """
        if not content:
            return ""
            
        DANGEROUS_TAGS = r"(script|iframe|object|embed|style|link|meta)"
        # Regex matches `<script...>`, `</script>`, etc.
        pattern_str = r"<\/?(?:script|iframe|object|embed|style|link|meta)\b[^>]*>"
        pattern = re.compile(pattern_str, re.IGNORECASE)
        
        if pattern.search(content):
            logger.warning("Dangerous HTML tags detected in markdown. Sanitizing content.")
            # Remove the dangerous tags
            content = pattern.sub("", content)
            
        return content
