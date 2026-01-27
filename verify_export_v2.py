import sys
import os
import logging

# Add project root to path
sys.path.append(os.getcwd())

from services.reporting.export_service import ExportService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_mock_state():
    return {
        "query": "Future of AI in Healthcare",
        "selected_papers": [
            {
                "paper_id": "p1",
                "title": "Deep Learning for Medical Imaging",
                "authors": "Smith et al.",
                "pdf_url": "http://example.com/p1.pdf"
            },
            {
                "paper_id": "p2",
                "title": "Ethical Considerations in AI Diagnostics",
                "authors": "Doe & Lee",
                "pdf_url": "http://example.com/p2.pdf"
            }
        ],
        "report_state": {
            "created_at": "2023-10-27",
            "metrics": {
                "completeness": 0.95,
                "factuality": 0.98
            },
            "abstract": "This report explores AI trends using å, é, î, ø, ü characters for Unicode testing.",
            "sections": [
                {
                    "section_id": "intro",
                    "title": "Introduction",
                    "section_index": "1",
                    "content": "**Artificial Intelligence** (AI) is transforming healthcare. This report explores current trends.\n\n**Key Objectives:**\n- Analyze recent advances\n- Discuss ethical challenges",
                    "status": "accepted"
                },
                {
                    "section_id": "methods",
                    "title": "Methodology",
                    "section_index": "2",
                    "content": "We conducted a literature review of 50 papers from top conferences.",
                    "status": "accepted",
                    "subsections": [
                        {
                            "section_id": "data_collection",
                            "title": "Data Collection",
                            "section_index": "2.1",
                            "content": "Papers were collected from ArXiv and PubMed using keyword search.",
                            "status": "accepted"
                        }
                    ]
                },
                {
                    "section_id": "conclusion",
                    "title": "Conclusion",
                    "section_index": "3",
                    "content": "AI shows great promise but requires rigorous validation.",
                    "status": "accepted"
                }
            ]
        }
    }

def verify_exports():
    state = create_mock_state()
    # Mock References with real-looking links as requested
    state["selected_papers"] = [
         {
            "paper_id": "p1",
            "title": "Deep Learning for Medical Imaging",
            "authors": "Smith et al.",
            "pdf_url": "https://doi.org/10.1000/xyz123"
        },
        {
            "paper_id": "p2",
            "title": "Ethical Considerations in AI Diagnostics",
            "authors": "Doe & Lee",
            "pdf_url": "https://doi.org/10.1000/abc456"
        }
    ]
    
    formats = ["markdown", "docx", "latex", "pdf"]
    
    output_dir = "test_outputs"
    os.makedirs(output_dir, exist_ok=True)
    
    for fmt in formats:
        logger.info(f"Testing export for format: {fmt}...")
        try:
            content = ExportService.export_report(state, fmt)
            
            # Determine extension
            ext = fmt
            if fmt == "markdown": ext = "md"
            if fmt == "latex": ext = "tex"
            
            filename = f"{output_dir}/report.{ext}"
            with open(filename, "wb") as f:
                f.write(content)
                
            size = os.path.getsize(filename)
            logger.info(f"✅ Success: {filename} created ({size} bytes)")
            
        except Exception as e:
            logger.error(f"❌ Failed to export {fmt}: {e}")

if __name__ == "__main__":
    verify_exports()
