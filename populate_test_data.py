import os
import networkx as nx
from datetime import datetime
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv(".env.local")
from database.db import SessionLocal, init_db
from database.models.auth_models import ResearchSession, User
from database.models.workflow_state_model import WorkflowState

def populate():
    init_db()
    db = SessionLocal()
    
    session_id = str(uuid4())
    user_id = str(uuid4())

    user = User(
        id=user_id,
        email="test_user_" + str(uuid4())[:8] + "@test.com",
        role="STUDENT",
        created_at=datetime.utcnow()
    )
    db.add(user)

    # Create a dummy session
    session = ResearchSession(
        session_id=session_id,
        user_id=user_id,
        query="real time data AI",
        status="RUNNING",
        last_updated=datetime.utcnow()
    )
    db.add(session)
    
    # Create the Knowledge Graph (NetworkX)
    G = nx.MultiDiGraph()
    G.add_node("real time data", type="concept", paper_frequency=1)
    G.add_node("machine learning", type="concept", paper_frequency=5)
    G.add_edge("machine learning", "real time data", relation="improves", type="concept_relation")
    
    # We add another node to affect clustering maybe
    G.add_node("streaming", type="concept", paper_frequency=2)
    G.add_edge("streaming", "real time data", relation="enables", type="concept_relation")
    
    kg_data = nx.node_link_data(G)
    
    state_data = {
        "knowledge_graph": kg_data,
        "global_analysis": {
            "key_concepts": [{"concept": "real time data"}, {"concept": "machine learning"}],
            "concept_relations": [
                {"source": "machine learning", "target": "real time data", "relation": "improves"}
            ]
        },
        "paper_relations": {},
        "paper_concepts": {}
    }
    
    # Create workflow state
    wfs = WorkflowState(
        query=session_id,
        user_id=user_id,
        state=state_data
    )
    db.add(wfs)
    
    db.commit()
    db.close()
    print("Database populated for diagnostics.")

if __name__ == "__main__":
    populate()
