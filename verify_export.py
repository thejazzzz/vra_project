
import os
import shutil
from services.reporting.export_service import ExportService

def test_export_service():
    print("Testing Export Service...")
    
    state = {
        "query": "Test Query",
        "report_state": {
            "sections": [
                {"title": "Intro", "content": "Hello World"}
            ]
        }
    }
    
    # 1. Test Bytes Return
    res_bytes = ExportService.export_report(state, "markdown")
    assert isinstance(res_bytes, bytes)
    assert b"Hello World" in res_bytes
    print("✓ Bytes return passed")
    
    # 2. Test File Write
    out_dir = "temp_export_test"
    out_file = os.path.join(out_dir, "report.md")
    try:
        res_path = ExportService.export_report(state, "markdown", output_path=out_file)
        assert res_path == out_file
        assert os.path.exists(out_file)
        with open(out_file, "rb") as f:
            content = f.read()
            assert b"Hello World" in content
        print("✓ File write passed")
    finally:
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)

    # 3. Test Validation
    # Safe cases
    assert ExportService.validate_markdown("Simple text")
    assert ExportService.validate_markdown("Math x < y and y > z")
    assert ExportService.validate_markdown("Arrows -> and <-")
    print("✓ Safe markdown passed")
    
    # Unsafe cases
    assert not ExportService.validate_markdown("<div>Content</div>")
    assert not ExportService.validate_markdown("Text <br> Text")
    assert not ExportService.validate_markdown("<script>alert(1)</script>")
    print("✓ Unsafe markdown blocked")
    
    print("All tests passed!")

if __name__ == "__main__":
    test_export_service()
