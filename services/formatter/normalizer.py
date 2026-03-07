# services/formatter/normalizer.py
from typing import Dict, Any, List, Tuple
from services.formatter.schema import FormattedReport, FormattedSection, FormattedReference, FormattedTable, FormattedFigure
import re
import uuid

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
             
        # 4. Extract Tables and Figures from section contents
        tables, figures = ReportNormalizer._extract_media_from_sections(normalized.sections)
        normalized.tables = tables
        normalized.figures = figures
             
        return normalized

    @staticmethod
    def _extract_media_from_sections(sections: List[FormattedSection]) -> Tuple[List[FormattedTable], List[FormattedFigure]]:
        tables = []
        figures = []
        t_index = 1
        f_index = 1
        
        # Regex for Markdown Images: ![caption](url)
        img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
        # Regex for basic Markdown Tables (content between pipes over multiple lines, roughly)
        table_pattern = re.compile(r'(?:\|.*\|\n)+')
        
        for sec in sections:
            content = sec.content
            
            # Find Figures
            for match in img_pattern.finditer(content):
                caption = match.group(1) or f"Figure {f_index}"
                path = match.group(2)
                figures.append(FormattedFigure(
                    id=str(uuid.uuid4()),
                    caption=caption,
                    path=path,
                    index=f_index
                ))
                f_index += 1
                
            # Find Tables
            for match in table_pattern.finditer(content):
                table_content = match.group(0)
                if "-" in table_content and "|" in table_content: # Basic sanity check for table header separator
                    tables.append(FormattedTable(
                        id=str(uuid.uuid4()),
                        caption=f"Table {t_index}", # Markdown doesn't have standard table captions natively
                        content=table_content.strip(),
                        index=t_index
                    ))
                    t_index += 1
                    
            if sec.subsections:
                sub_t, sub_f = ReportNormalizer._extract_media_from_sections(sec.subsections)
                # Adjust indices for sub-extractions to maintain sequence
                for t in sub_t:
                    t.index = t_index
                    t.caption = f"Table {t_index}"
                    tables.append(t)
                    t_index += 1
                for f in sub_f:
                    f.index = f_index
                    f.caption = f"Figure {f_index}"
                    figures.append(f)
                    f_index += 1
                    
        return tables, figures

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
