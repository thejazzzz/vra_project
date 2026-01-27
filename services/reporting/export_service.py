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
    def validate_markdown(content: str) -> bool:
        """
        Validates markdown content by checking for basic HTML tag structure.
        
        Returns True if safe (no HTML tags detected), False otherwise.
        Does NOT validate Pandoc compatibility or advanced structure.
        """
        if not content:
            return True
            
        # Tighter Regex: Matches <tag> or </tag> where tag starts with a letter.
        # This avoiding matching math (x < y) or arrows (Generic<T> might match if T starts with letter, but acceptable risk for now vs complexity)
        # Actually Generic<T> is NOT an HTML tag, but basic regex might flag it. 
        # <[a-zA-Z] matches <T
        # We can accept that risk or require attributes/closing.
        # Ideally, we want to block <div>, <script>, <a> etc.
        
        if re.search(r"<\/?[a-zA-Z][^>]*>", content):
            logger.warning("Markdown validation failed: HTML tag detected.")
            return False
            
        return True
