# services/formatter/normalizer.py
from typing import Dict, Any, List
from services.formatter.schema import FormattedReport, FormattedSection, FormattedReference

class ReportNormalizer:
    @staticmethod
    def normalize(state: Dict[str, Any]) -> FormattedReport:
        """
        Converts the raw ReportState into a clean FormattedReport.
        """
        report_state = state.get("report_state", {})
        query = state.get("query", "Research Report")
        
        # 1. Basic Metadata
        normalized = FormattedReport(
            title=query.strip() if query and query.strip() else "Research Report",
            date=report_state.get("created_at", "Unknown Date"),
            authors=["AI Researcher"], # Placeholder or pull from config
            abstract=report_state.get("abstract"), # Fix: Populate abstract
            meta=report_state.get("metrics", {})
        )
        
        # 2. Sections
        # The report_state["sections"] is a flat list with possible 'subsections' nested, 
        # or flat list with 'depends_on' logic. 
        # Based on state_schema.py, it's a list. We assume they are ordered by appearance or we rely on 'section_index'.
        
        raw_sections = report_state.get("sections", [])
        
        # Sort by section_index if available ("1", "1.1", "2")
        # If not, use list order
        try:
            raw_sections = sorted(raw_sections, key=lambda x: [int(p) for p in x.get("section_index", "0").split(".")])
        except (ValueError, TypeError, AttributeError):
            pass # Fallback to list order
             
        normalized.sections = ReportNormalizer._process_sections(raw_sections)
        
        # 3. References (Mocking from selected_papers for now)
        papers = state.get("selected_papers", [])
        for i, paper in enumerate(papers, 1):
             normalized.references.append(FormattedReference(
                 id=paper.get("paper_id", str(i)),
                 index=i,
                 text=f"{paper.get('title', 'Unknown Title')} - {paper.get('authors', 'Unknown Authors')}",
                 url=paper.get("pdf_url")
             ))
             
        return normalized

    @staticmethod
    def _process_sections(sections: List[Dict[str, Any]], level: int = 1) -> List[FormattedSection]:
        result = []
        for s in sections:
            # Skip unaccepted sections? Or include as draft?
            # if s.get("status") != "accepted": continue
            
            f_sec = FormattedSection(
                id=s.get("section_id", "unknown"),
                title=s.get("title", "Untitled Section"),
                level=level,
                numbering=s.get("section_index", ""),
                content=s.get("content") or "*Content pending...*"
            )
            
            # Recurse if subsections exist
            if "subsections" in s:
                f_sec.subsections = ReportNormalizer._process_sections(s["subsections"], level + 1)
            
            result.append(f_sec)
        return result
