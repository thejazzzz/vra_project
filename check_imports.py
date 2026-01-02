import sys
import os

# Add current directory to sys.path
sys.path.append(os.getcwd())

print(f"CWD: {os.getcwd()}")
print(f"Path: {sys.path}")

try:
    import fitz
    print("SUCCESS: import fitz")
except ImportError as e:
    print(f"FAILURE: import fitz - {e}")

try:
    from services.research_service import ingest_local_file
    print("SUCCESS: from services.research_service import ingest_local_file")
except ImportError as e:
    print(f"FAILURE: import ingest_local_file - {e}")
except Exception as e:
    print(f"FAILURE: other error importing service - {e}")
