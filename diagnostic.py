import json
import re
import networkx as nx
import sys
from dotenv import load_dotenv
load_dotenv(".env.local")
from database.db import SessionLocal
from database.models.auth_models import ResearchSession
from database.models.workflow_state_model import WorkflowState

def canonical_concept_id(text: str) -> str:
    if not text: return ""
    text = text.strip().lower().replace("-", " ").replace("_", " ")
    return re.sub(r'\s+', ' ', text)

def main():
    db = SessionLocal()
    # Get latest active session
    latest_session = db.query(ResearchSession).order_by(ResearchSession.last_updated.desc()).first()
    if not latest_session:
        print(json.dumps({"error": "No session found"}))
        return

    session_id = latest_session.session_id
    user_id = latest_session.user_id

    state_row = db.query(WorkflowState).filter(WorkflowState.query == session_id).filter(WorkflowState.user_id == user_id).first()
    if not state_row:
        print(json.dumps({"error": "No state found"}))
        return

    state = state_row.state
    kg_data = state.get("knowledge_graph", {})
    
    # Reconstruct G
    try:
        if "directed" in kg_data: # nx node_link format
             G = nx.node_link_graph(kg_data)
        else:
             G = nx.MultiDiGraph()
    except Exception as e:
        G = nx.MultiDiGraph()

    target_concept = "real time data"
    c_id = canonical_concept_id(target_concept)

    exists = c_id in G.nodes

    # find origins
    global_analysis = state.get("global_analysis", {})
    paper_relations = state.get("paper_relations", {})
    paper_concepts = state.get("paper_concepts", {})
    
    intro_global = False
    intro_paper_relations = False
    intro_paper_concepts = False
    intro_user = False

    if c_id in [canonical_concept_id(c.get("concept","") if isinstance(c, dict) else c) for c in global_analysis.get("key_concepts", [])]:
        intro_global = True
    
    # Check global relations
    for rel in global_analysis.get("concept_relations", []):
         if canonical_concept_id(rel.get("source", "")) == c_id or canonical_concept_id(rel.get("target", "")) == c_id:
             intro_global = True

    for pid, rels in paper_relations.items():
        for r in rels:
             if canonical_concept_id(r.get("source", "")) == c_id or canonical_concept_id(r.get("target", "")) == c_id:
                 intro_paper_relations = True

    for pid, concepts in paper_concepts.items():
        for c in concepts:
            if canonical_concept_id(c) == c_id:
                intro_paper_concepts = True

    # User overrides
    overrides = [] # not strictly saved in state in this implementation unless run_meta

    # structural_metrics
    paper_frequency = 0
    degree = 0
    neighbors_list = []
    clustering = 0.0

    if exists:
        paper_frequency = G.nodes[c_id].get("paper_frequency", 0)
        
        # for clustering we need undirected simple graph without meta
        G_simple = nx.Graph()
        for u, v, d in G.edges(data=True):
             if d.get("type") == "meta" or d.get("relation") == "appears_in": continue
             if u in G.nodes and G.nodes[u].get("type") != "concept": continue
             if v in G.nodes and G.nodes[v].get("type") != "concept": continue
             G_simple.add_edge(u, v)
        
        if c_id in G_simple:
            degree = G_simple.degree(c_id)
            neighbors_list = list(G_simple.neighbors(c_id))
            clustering = nx.clustering(G_simple, c_id)
        
    # normalization_metrics
    max_papers = 0
    for n, d in G.nodes(data=True):
        if d.get("type") == "concept":
            pf = d.get("paper_frequency", 0)
            if pf > max_papers:
                max_papers = pf

    norm_coverage = (paper_frequency / max_papers) if max_papers > 0 else 0.0
    raw_gap = 0.5 * (1.0 - norm_coverage) + 0.3 * (1.0 - clustering) + 0.2 * 1.0
    final_conf = round(min(raw_gap, 0.95), 2)

    # eligibility
    elig_current = paper_frequency <= 2 and final_conf > 0.6
    elig_min1 = paper_frequency <= 1 and final_conf > 0.6
    elig_min2 = paper_frequency <= 2 and final_conf > 0.6

    class_reason = "structural_gap"
    if paper_frequency == 0 and exists:
        if intro_global and not intro_paper_relations and not intro_paper_concepts:
            class_reason = "inferred_global_theme"
        elif degree == 0:
            class_reason = "isolated_node"
        else:
            class_reason = "normalization_artifact"
            
    recommendation = "keep_as_gap"
    if paper_frequency == 0:
        recommendation = "downgrade_to_inferred"

    out = {
        "1. concept_exists_in_graph": exists,
        "2. concept_origin": {
            "introduced_via_global_analysis": intro_global,
            "introduced_via_paper_relations": intro_paper_relations,
            "introduced_via_paper_concepts": intro_paper_concepts,
            "introduced_via_user_override": intro_user
        },
        "3. structural_metrics": {
            "paper_frequency": paper_frequency,
            "degree": degree,
            "neighbors": neighbors_list,
            "clustering_coefficient": round(clustering, 4) if exists else "undefined",
            "betweenness_centrality": "not_computed_for_performance"
        },
        "4. normalization_metrics": {
            "max_benchmark": max_papers,
            "normalized_coverage": round(norm_coverage, 4),
            "raw_gap_score_before_clipping": round(raw_gap, 4),
            "final_confidence_score": final_conf
        },
        "5. eligibility_check": {
            "eligible_under_current_rules": elig_current,
            "would_be_eligible_if_min_support_1": elig_min1,
            "would_be_eligible_if_min_support_2": elig_min2
        },
        "6. classification_reason": class_reason,
        "7. recommendation": recommendation
    }

    with open('diag_output_clean.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)

if __name__ == "__main__":
    main()
