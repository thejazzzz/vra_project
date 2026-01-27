# services/formatter/formatter_core.py
from typing import Dict, Any
from services.formatter.schema import FormattedReport
from services.formatter.normalizer import ReportNormalizer
# Import renderers (lazy import or direct)
# from services.formatter.renderers.markdown_renderer import MarkdownRenderer
# from services.formatter.renderers.docx_renderer import DocxRenderer
# from services.formatter.renderers.pdf_renderer import PdfRenderer
# from services.formatter.renderers.latex_renderer import LatexRenderer

class ReportFormatter:
    
    @staticmethod
    def format_report(state: Dict[str, Any], export_format: str) -> bytes:
        """
        Main entry point.
        1. Normalize content
        2. Select Renderer
        3. Render to bytes
        """
        # 1. Normalize
        normalized_report = ReportNormalizer.normalize(state)
        
        export_format = export_format.lower()
        
        # 2. Dispatch
        if export_format == "markdown" or export_format == "md":
            from services.formatter.renderers.markdown_renderer import MarkdownRenderer
            return MarkdownRenderer.render(normalized_report)
            
        elif export_format == "docx":
            from services.formatter.renderers.docx_renderer import DocxRenderer
            return DocxRenderer.render(normalized_report)
            
        elif export_format == "pdf":
            from services.formatter.renderers.pdf_renderer import PdfRenderer
            return PdfRenderer.render(normalized_report)
            
        elif export_format == "latex" or export_format == "tex":
            from services.formatter.renderers.latex_renderer import LatexRenderer
            return LatexRenderer.render(normalized_report)
            
        else:
            raise ValueError(f"Unsupported format: {export_format}")
