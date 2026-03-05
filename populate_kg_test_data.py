import os
from datetime import datetime
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv(".env.local")
from database.db import SessionLocal, init_db
from database.models.evaluation_model import GoldStandard
from database.models.graph_model import Graph

def populate_kg_test():
    init_db()
    db = SessionLocal()
    
    query = "Explain Graph Neural Networks"
    
    # 1. Add Gold Standard triplets
    gold_data = [
        {"subject": "GCN", "predicate": "extends", "object": "GNN"},
        {"subject": "GCN", "predicate": "improves", "object": "Accuracy"},
        {"subject": "Graph", "predicate": "contains", "object": "Nodes"},
    ]
    
    for g in gold_data:
        gs = GoldStandard(
            query=query,
            subject=g["subject"],
            predicate=g["predicate"],
            object=g["object"],
            source="MockDataset"
        )
        db.add(gs)
        
    # 2. Add Generated Graph
    # We will make 1 True Positive, 1 False Positive, 1 False Negative (missed 'contains' relation).
    kg_data = {
        "links": [
            # True Positive (High Confidence -> Bins)
            {"source": "GCN", "target": "GNN", "relation": "extends", "confidence": 0.9},
            
            # False Positive (Low Confidence -> Bins)
            {"source": "GCN", "target": "Graph", "relation": "is_a", "confidence": 0.3},
            
            # Additional True Positive (Medium Confidence -> Bins)
            {"source": "GCN", "target": "Accuracy", "relation": "improves", "confidence": 0.6}
        ],
        "graph": {
            "meta": {"run_id": str(uuid4()), "model_version": "test_model"}
        }
    }
    
    graph_entry = Graph(
        query=query,
        user_id="test_user",
        knowledge_graph=kg_data,
        citation_graph={}
    )
    db.add(graph_entry)
    
    db.commit()
    db.close()
    print("KG database populated for evaluation.")

if __name__ == "__main__":
    populate_kg_test()
