import time
import logging
from dotenv import load_dotenv
import os

load_dotenv()

from clients.semantic_scholar_client import search_semantic_scholar

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_s2")

def test_s2_client():
    query = "Large Language Models"
    
    print("--- STARTING RATE LIMIT TEST ---")
    start_time = time.time()
    
    # Request 1
    print("Request 1...")
    results1 = search_semantic_scholar(query, limit=1)
    
    # Request 2
    print("Request 2...")
    results2 = search_semantic_scholar("Graph Neural Networks", limit=1)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"--- TEST COMPLETE ---")
    print(f"Duration for 2 requests: {duration:.4f}s")
    
    if duration < 1.0:
        print("❌ Rate limit FAILED (too fast)")
    else:
        print("✅ Rate limit PASSED (>= 1.0s)")

    assert duration >= 1.0, f"Rate limit not enforced: 2 requests completed in {duration:.4f}s (expected >= 1.0s)"


    if results1:
        p = results1[0]
        print("\n--- METADATA CHECK ---")
        print(f"Title: {p.get('title')}")
        print(f"PDF URL: {p.get('pdf_url')}")
        print(f"Citation Count: {p.get('citation_count')}")
        print(f"Reference Count: {p.get('reference_count')}")
        
        meta = p.get("metadata", {})
        if "openAccessPdf" in meta:
            print(f"OpenAccessPDF Raw: {meta['openAccessPdf']}")
        else:
            print("No OpenAccessPDF field found (might be null for this paper)")

        if "referenceCount" not in meta:
            print("❌ 'referenceCount' missing from metadata")
        else:
            print(f"✅ 'referenceCount' present: {meta['referenceCount']}")

    else:
        print("❌ No results found (Check API Key or Connection)")

if __name__ == "__main__":
    test_s2_client()
