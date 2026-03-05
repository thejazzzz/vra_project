import sys
import os
import time
import logging
from uuid import uuid4
from dotenv import load_dotenv

os.environ["APP_ENV"] = "test"
load_dotenv(".env.local")

from database.db import init_db
init_db()

sys.path.append(os.getcwd())
logging.basicConfig(level=logging.ERROR)

from services.state_service import save_state_for_query
from database.models.auth_models import User, ResearchSession, SessionStatus
from database.db import SessionLocal
from datetime import datetime

# Import actual agents
from services.research_service import generate_sub_queries
from agents.semantic_scholar_agent import semantic_scholar_agent
from agents.paper_summarization_agent import paper_summarization_agent
from agents.graph_builder_agent import graph_builder_agent
from agents.gap_analysis_agent import gap_analysis_agent
from services.reporting.section_planner import SectionPlanner
from services.reporting.reporting_service import InteractiveReportingService

import asyncio

async def run_real_benchmarks():
    print("Executing System Benchmark with REAL API Calls...\n")
    timings = {}
    
    session_id = str(uuid4())
    user_id = str(uuid4())
    
    # Create mock user in DB for auth checks
    db = SessionLocal()
    user = User(id=user_id, email=f"bench_{user_id[:6]}@test.com", role="ADMIN")
    db.add(user)
    session = ResearchSession(session_id=session_id, user_id=user_id, query="Graph Neural Networks in healthcare", status=SessionStatus.RUNNING)
    db.add(session)
    db.commit()
    db.close()
    
    state = {
        "query": "Graph Neural Networks in healthcare",
        "user_id": user_id,
        "audience": "general",
        "collected_papers": [],
        "selected_papers": [],
        "added_papers": []
    }
    state["papers_to_fetch"] = 3 # Keep small for benchmark speed
    
    # 1. Query Parsing / Expansion
    start_time = time.time()
    await generate_sub_queries(state["query"])
    timings["Query Parsing Execution Time"] = time.time() - start_time
    print(f"Query Parsing done: {timings['Query Parsing Execution Time']:.2f}s")
    
    # 2. Literature Retrieval
    start_time = time.time()
    papers = await semantic_scholar_agent.run(state["query"], limit=3)
    state["selected_papers"] = papers
    timings["Literature Retrieval Execution Time"] = time.time() - start_time
    print(f"Literature Retrieval done: {timings['Literature Retrieval Execution Time']:.2f}s")
    
    # 2.5 Paper Summarization & Extraction
    start_time = time.time()
    state = paper_summarization_agent.run(state)
    timings["Extraction Execution Time"] = time.time() - start_time
    print(f"Extraction done: {timings['Extraction Execution Time']:.2f}s")
    
    # 3. Graph Construction
    start_time = time.time()
    state = graph_builder_agent.run(state)
    timings["Graph Construction Execution Time"] = time.time() - start_time
    print(f"Graph Construction done: {timings['Graph Construction Execution Time']:.2f}s")
    
    # 4. Gap Analysis
    start_time = time.time()
    state = gap_analysis_agent.run(state)
    timings["Gap Analysis Execution Time"] = time.time() - start_time
    print(f"Gap Analysis done: {timings['Gap Analysis Execution Time']:.2f}s")
    
    # 5. Report Generation (1 Section)
    start_time = time.time()
    state["report_state"] = SectionPlanner.initialize_report_state(state)
    save_state_for_query(session_id, state, user_id)
    
    if state["report_state"].get("sections"):
        first_section_id = state["report_state"]["sections"][0]["section_id"]
        try:
            InteractiveReportingService.generate_section(session_id, user_id, first_section_id)
        except Exception as e:
            print(f"Section generation error: {e}")
    else:
        print("No sections planned.")
    
    timings["Report Section Generation Time"] = time.time() - start_time
    print(f"Report Section Generation done: {timings['Report Section Generation Time']:.2f}s")

    import json
    with open("benchmark_results.json", "w") as f:
        json.dump(timings, f, indent=4)
        
    print("\nCalculations saved to benchmark_results.json")
    
    # Clean up DB
    db = SessionLocal()
    db.query(ResearchSession).filter(ResearchSession.session_id == session_id).delete()
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    db.close()

if __name__ == "__main__":
    asyncio.run(run_real_benchmarks())
