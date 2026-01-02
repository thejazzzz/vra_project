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
    def export_report(state: Dict[str, Any], format: str, output_path: Optional[str] = None) -> Union[bytes, str]:
        """
        Exports the report to the specified format.
        
        Args:
            state: The full report state dictionary.
            format: Target format ('pdf', 'docx', 'markdown').
            output_path: Optional file path to write the output to.

        Returns:
            bytes: The binary content if output_path is None.
            str: The output_path if writing to file was successful.
        """
        # 1. Validate Format
        format = format.lower()
        if format not in ["pdf", "docx", "markdown"]:
            raise ValueError(f"Unsupported export format: {format}")

        # 2. Generate Content (Stub -> Real Bytes placeholders)
        content_bytes = b""
        
        # Assemble text (simple concatenation for now)
        report_state = state.get("report_state", {})
        sections = report_state.get("sections", [])
        full_text = f"# Report: {state.get('query', 'Untitled')}\n\n"
        for section in sections:
            full_text += f"## {section.get('title', 'Unknown')}\n\n"
            full_text += f"{section.get('content', '')}\n\n"
            
        # Mock encoding for different formats
        if format == "markdown":
            content_bytes = full_text.encode('utf-8')
        elif format == "pdf":
            # STUB: PDF export is currently a placeholder.
            # Requires external libraries like reportlab or weasyprint.
            raise NotImplementedError("PDF export is not yet implemented. Please use 'markdown' format.")

        elif format == "docx":
            # STUB: DOCX export is currently a placeholder.
            # Requires external libraries like python-docx.
            raise NotImplementedError("DOCX export is not yet implemented. Please use 'markdown' format.")


        # 3. Handle Output
        if output_path:
            try:
                # Create parent directories
                parent_dir = os.path.dirname(os.path.abspath(output_path))
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
                
                with open(output_path, "wb") as f:
                    f.write(content_bytes)
                return output_path
            except OSError as e:
                logger.error(f"Failed to write export to {output_path}: {e}")
                raise 
        
        return content_bytes

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
