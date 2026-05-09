
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
S2_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

S2_SEARCH_FIELDS = [
    "paperId",
    "title",
    "abstract",
    "authors",
    "year",
    "venue",
    "externalIds",
    "url",
    "referenceCount",
    "citationCount",
    "influentialCitationCount",
    "openAccessPdf",
]

def test_search(with_key=True):
    params = {
        "query": "transformer neural networks",
        "limit": 1,
        "fields": ",".join(S2_SEARCH_FIELDS),
    }

    key = API_KEY if with_key else None
    headers = {"x-api-key": key} if key else {}
    
    print(f"\n--- Testing S2 API {'WITH' if with_key else 'WITHOUT'} Key ---")
    if with_key:
        print(f"Key: {key[:4]}...{key[-4:] if key else 'None'}")
    
    try:
        resp = requests.get(S2_API_URL, params=params, headers=headers, timeout=20)
        print(f"Status Code: {resp.status_code}")
        print(f"Response Body: {resp.text}")
        
        if resp.status_code == 200:
            print("Status: SUCCESS")
        elif resp.status_code == 403:
            print("Status: FORBIDDEN")
        elif resp.status_code == 429:
            print("Status: RATE LIMITED")
            
    except Exception as e:
        print(f"Error: {e}")

def test_search_minimal(with_key=True):
    params = {
        "query": "transformer",
        "limit": 1,
        "fields": "paperId,title",
    }
    key = API_KEY if with_key else None
    headers = {"x-api-key": key} if key else {}
    print(f"\n--- Testing MINIMAL Fields {'WITH' if with_key else 'WITHOUT'} Key ---")
    try:
        resp = requests.get(S2_API_URL, params=params, headers=headers, timeout=20)
        print(f"Status Code: {resp.status_code}")
        print(f"Response Body: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search(with_key=True)
    test_search(with_key=False)
    test_search_minimal(with_key=True)
