import asyncio
import logging
import sys

# Configure logging to print to stdout
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

from agents.data_acquisition_agent import data_acquisition_agent

async def main():
    query = "attention is all you need"
    print(f"Running acquisition for: {query}")
    
    # We set expand_citations=True to test the snowballing logic with OpenAlex
    papers = await data_acquisition_agent.run(query, limit=2, expand_citations=True)
    
    print("\n--- RESULTS ---")
    print(f"Total merged papers: {len(papers)}")
    
    for idx, p in enumerate(papers[:5]): # show top 5
        print(f"\nPaper {idx+1}: {p.get('title')}")
        print(f"  Canonical ID: {p.get('canonical_id')}")
        print(f"  Sources: {p.get('sources')}")
        
        meta = p.get("metadata", {})
        refs = meta.get("references", [])
        concepts = meta.get("concepts", [])
        
        print(f"  Citation Count: {meta.get('citationCount')}")
        print(f"  References Count: {len(refs)}")
        if refs:
            print(f"  Sample Reference ID: {refs[0].get('paperId')}")
            
        print(f"  Concepts Count: {len(concepts)}")
        if concepts:
            print(f"  Sample Concepts: {', '.join(concepts[:3])}")

if __name__ == "__main__":
    # Workaround for ProactorEventLoop closing issue on Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
