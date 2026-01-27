import sys
import os
import logging
import traceback
from services.reporting.export_service import ExportService

# Add project root to path
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_mock_state():
    return {
        "query": "Test",
        "report_state": {
            "created_at": "2023-10-27",
            "sections": [
                {
                    "section_id": "intro",
                    "title": "Introduction",
                    "content": "Hello World",
                    "status": "accepted"
                }
            ]
        }
    }

def debug_pdf():
    state = create_mock_state()
    try:
        content = ExportService.export_report(state, "pdf")
        print(f"Success! {len(content)} bytes")
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    debug_pdf()
