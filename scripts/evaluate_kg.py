# scripts/evaluate_kg.py
import sys
import os
import json
from typing import List, Dict, Tuple
from uuid import uuid4

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv
load_dotenv(".env.local")

from sqlalchemy import insert
from database.db import SessionLocal, engine, Base
from database.models.graph_model import Graph
from database.models.evaluation_model import GoldStandard, EvaluationRun
from services.graph_service import calculate_confidence

# Ensure tables exist
Base.metadata.create_all(bind=engine)

def normalize(text: str) -> str:
    return text.strip().lower().replace("-", " ").replace("_", " ")

def evaluate_query(query: str):
    print(f"\n🧪 Evaluating Query: '{query}'")
    
    with SessionLocal() as db:
        # 1. Load Ground Truth
        gold_rows = db.query(GoldStandard).filter(GoldStandard.query == query).all()
        if not gold_rows:
            print("❌ No Gold Standard data found for this query.")
            return
        
        gold_triplets = set()
        matched_gold = set()
        for g in gold_rows:
            gold_triplets.add((normalize(g.subject), normalize(g.object), normalize(g.predicate)))
        
        print(f"✅ Loaded {len(gold_triplets)} Gold Standard triplets.")

        # 2. Load KG
        kg_row = db.query(Graph).filter(Graph.query == query).order_by(Graph.updated_at.desc()).first()
        if not kg_row or not kg_row.knowledge_graph:
            print("❌ No Knowledge Graph found for this query.")
            return

        kg = kg_row.knowledge_graph
        kg_links = kg.get("links", [])
        
        # 3. Compute Metrics
        tp = 0
        fp = 0
        
        # For Calibration
        bins = {
            "0.0-0.4": {"total": 0, "correct": 0},
            "0.4-0.7": {"total": 0, "correct": 0},
            "0.7-1.0": {"total": 0, "correct": 0}
        }
        
        print(f"🔍 Analyzing {len(kg_links)} generated edges...")
        
        for link in kg_links:
            # Skip meta edges for evaluation
            # Assuming 'type' isn't on link usually, but check relation
            if link.get("relation") == "appears_in": continue
            
            s = normalize(link.get("source", ""))
            t = normalize(link.get("target", ""))
            r = normalize(link.get("relation", ""))
            conf = link.get("confidence", 0.5)
            
            # Match Logic (Soft match on relation often needed, but assume strict for now)
            # Simple check: (s, t) mostly matters, relation is secondary
            match = False
            matched_triplet = None
            
            # Check exact match
            if (s, t, r) in gold_triplets:
                match = True
                matched_triplet = (s, t, r)
            else:
                 # Check if ANY relation exists between s and t in Gold (Relaxed match)
                 for gs, gt, gr in gold_triplets:
                     if s == gs and t == gt:
                         match = True
                         matched_triplet = (gs, gt, gr)
                         break
            
            if match:
                # Precision/Recall Logic: Don't double count Gold triplets
                if matched_triplet not in matched_gold:
                    tp += 1
                    matched_gold.add(matched_triplet)
                # If already matched, we treat it as a duplicate hit - technically TP for this edge,
                # but for Recall we care about Unique Gold Recovered.
                # Standard Message Understanding Conference (MUC) metrics would punish duplicate extraction as FP?
                # Let's keep TP for Precision, but Recall uses Unique Matches.
                # Wait, User Request: "only increment tp when the matched gold triplet is not yet in that set"
                # So we ONLY count TP for the FIRST match.
                # subsequent matches are redundant? If so, they are effectively FPs?
                # User says: "only increment tp when the matched gold triplet is not yet in that set"
                # This implies strict 1:1 mapping (or close to it).
                pass
            else:
                fp += 1
                
            # Binning
            bin_key = "0.0-0.4"
            if conf >= 0.7: bin_key = "0.7-1.0"
            elif conf >= 0.4: bin_key = "0.4-0.7"
            
            bins[bin_key]["total"] += 1
            if match: bins[bin_key]["correct"] += 1

        fn = len(gold_triplets) - len(matched_gold)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        print(f"📊 Results:")
        print(f"  Precision: {precision:.2f}")
        print(f"  Recall:    {recall:.2f}")
        print(f"  F1 Score:  {f1:.2f}")
        
        # Compute Calibration
        calibration_metrics = {}
        print("\n🎯 Calibration:")
        for k, v in bins.items():
            if v["total"] > 0:
                prec = v["correct"] / v["total"]
                print(f"  [{k}]: {prec:.2f} ({v['correct']}/{v['total']})")
                calibration_metrics[f"precision_bin_{k}"] = prec
            else:
                print(f"  [{k}]: N/A (0)")

        # 4. Save Run
        run_meta = kg.get("graph", {}).get("meta", {})
        
        eval_run = EvaluationRun(
            run_id=run_meta.get("run_id", str(uuid4())),
            model_version=run_meta.get("model_version", "unknown"),
            query=query,
            precision=precision,
            recall=recall,
            f1_score=f1,
            calibration_metrics=calibration_metrics,
            details={"tp": tp, "fp": fp, "fn": fn}
        )
        db.add(eval_run)
        db.commit()
        print("✅ Evaluation saved.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, help="Query to evaluate", required=True)
    args = parser.parse_args()
    
    evaluate_query(args.query)
