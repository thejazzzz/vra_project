
import asyncio
import logging
import sys
import os
import requests

# Add the project root to sys.path
sys.path.append(os.getcwd())

from clients.semantic_scholar_client import S2_FIELDS, API_KEY

async def test_details():
    # Test a known paper with many citations
    # "Attention is all you need" - S2 ID: 204e3073b646c265691062973161c28c8d8b67f1
    paper_id = "204e3073b646c265691062973161c28c8d8b67f1"
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
    params = {"fields": ",".join(S2_FIELDS)}
    headers = {"x-api-key": API_KEY} if API_KEY else {}
    
    print(f"Fetching details for paper: {paper_id}")
    resp = requests.get(url, params=params, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        refs = data.get("references", [])
        print(f"Success! Found {len(refs)} references.")
        if refs:
            print(f"First ref: {refs[0]}")
    else:
        print(f"Failed to fetch details: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    asyncio.run(test_details())
