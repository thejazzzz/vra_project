# services/trend_analysis_service.py
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple
import math
import statistics
import logging

logger = logging.getLogger(__name__)

def detect_concept_trends(
    papers: List[Dict[str, Any]], 
    concepts_per_paper: Dict[str, List[str]],
    paper_relations: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    window: Optional[Tuple[str, str]] = None
) -> Dict[str, Any]:
    """
    Detects temporal trends with scientific validity enforcement.
    
    Features:
    1. **Provenance**: Links trends to specific paper IDs.
    2. **Scope**: Classifies trends as Global, Subfield, or Niche.
    3. **Stability**: Detects Volatile vs Stable trends based on variance.
    4. **Relationship Evolution**: Tracks semantic drift via co-occurrence.
    5. **Confidence**: Statistical NCF-based scoring.

    Returns:
        Dict[str, Any] with keys:
        - "metadata": Dict containing processing info
            - "window_used": {"start": int, "end": int}
        - "trends": Dict[str, Dict] mapping concept_string -> trend_metrics
            Each trend_metrics dict contains:
            - "status": str ("Emerging", "Saturated", "Declining", "Stable", "Sporadic", "New")
            - "scope": str ("Global", "Subfield", "Niche")
            - "stability": str ("Volatile", "Stable", "Transient", "Unknown")
            - "semantic_drift": str ("High", "Moderate", "Low", "Unknown")
            - "is_trend_valid": bool
            - "growth_rate": float
            - "trend_confidence": float (0.0 - 1.0)
            - "total_count": int
            - "last_active_year": int
            - "trend_vector": List[Dict] (Yearly breakdown)
                - "year": int
                - "count": int
                - "norm_freq": float
                - "paper_ids": List[str]
                - "top_related": List[str]
    """
    
    # Data structures for aggregation
    # trends[concept][year] = { count: int, paper_ids: set, relations: dict }
    trends_data = defaultdict(lambda: defaultdict(lambda: {
        "count": 0, 
        "paper_ids": set(), 
        "relations": defaultdict(int)
    }))
    
    global_papers_per_year = defaultdict(int)
    total_papers_in_window = 0
    
    # Parse window strict validation
    start_year = 0
    end_year = 9999
    
    if window:
        try:
            # Type and Length check
            if not isinstance(window, (tuple, list)) or len(window) != 2:
                raise ValueError(f"Window must be a tuple/list of 2 items, got: {window}")
            
            # Conversion check
            s_val = int(window[0])
            e_val = int(window[1])
            
            # Logic check
            if s_val > e_val:
                raise ValueError(f"Start year ({s_val}) cannot be greater than end year ({e_val})")
            if s_val < 1900 or e_val > 2100: # Reasonable bounds check
                logger.warning(f"Window years ({s_val}-{e_val}) are outside typical range (1900-2100). Proceeding, but verify input.")
                
            start_year = s_val
            end_year = e_val
            
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid window parameter: {window}. Error: {e}")
            raise ValueError(f"Invalid window parameter: {e}") from e

    # Pass 1 & 2: Aggregation
    for paper in papers:
        pid = paper.get("canonical_id")
        year_raw = paper.get("year") or paper.get("publication_year") or paper.get("published_year")
        
        if not pid or not year_raw:
            continue
            
        try:
            year_int = int(year_raw)
        except (ValueError, TypeError):
            continue
            
        # Apply Temporal Window
        if year_int < start_year or year_int > end_year:
            continue
            
        global_papers_per_year[year_int] += 1
        total_papers_in_window += 1
        
        # Get concepts for this paper
        categories = concepts_per_paper.get(pid, [])
        # Get relations for this paper (if available) -> simple list of connected concepts
        # We derive this from paper_relations or simple co-occurrence within the paper
        # For efficiency, we'll use co-occurrence within the paper's concept list as a proxy for "relations"
        # AND explicit relations if provided.
        
        current_paper_concepts = set([c.lower().strip() for c in categories])
        
        # Explicit relations for this paper
        explicit_relations = set()
        if paper_relations and pid in paper_relations:
            for rel in paper_relations[pid]:
                src = rel.get("source", "").lower().strip()
                tgt = rel.get("target", "").lower().strip()
                if src and tgt:
                    explicit_relations.add((src, tgt))
                    explicit_relations.add((tgt, src))

        for concept in categories:
            c_norm = concept.lower().strip()
            
            # Update Concept Stats
            year_bucket = trends_data[c_norm][year_int]
            year_bucket["count"] += 1
            year_bucket["paper_ids"].add(pid)
            
            # Update Relations (Co-occurrence + Explicit)
            # 1. Co-occurrence
            for other in current_paper_concepts:
                if other != c_norm:
                    year_bucket["relations"][other] += 1
            
            # 2. Explicit
            # (Already covered if explicit relations are subset of concepts, but let's be safe)
            # If we wanted to track ONLY explicit, we would iterate explicit_relations.
            # For now, co-occurrence is a safer fallback for "Context".

    final_trends = {}
    
    # Pass 3: Metric Calculation
    for concept, yearly_data in trends_data.items():
        years = sorted(yearly_data.keys())
        if not years:
            continue
            
        total_count = sum(y["count"] for y in yearly_data.values())
        
        # 1. Scope Classification
        # Global > 20%, Subfield 5-20%, Niche < 5%
        # relative to TOTAL papers in window (or corpus if no window)
        # Avoid div/0
        corpus_share = total_count / max(1, total_papers_in_window)
        if corpus_share > 0.20:
            scope = "Global"
        elif corpus_share > 0.05:
            scope = "Subfield"
        else:
            scope = "Niche"

        # 2. Status & Growth
        # Calculate Normalized Frequency (NCF) per year
        trend_vector = []
        ncf_values = []
        
        has_relations = False
        
        for y in years:
            data = yearly_data[y]
            ncf = data["count"] / max(1, global_papers_per_year[y])
            ncf_values.append(ncf)
            
            # Top 3 related concepts for this year
            top_related = sorted(data["relations"].items(), key=lambda x: x[1], reverse=True)[:3]
            if top_related: 
                has_relations = True
            
            trend_vector.append({
                "year": y,
                "count": data["count"],
                "norm_freq": round(ncf, 4),
                "paper_ids": list(data["paper_ids"]), # Provenance
                "top_related": [k for k, v in top_related]
            })

        # Growth Rate (Last year vs Prev year)
        # Handle sparse data
        growth_rate = 0.0
        status = "Stable"
        
        if len(years) >= 2:
            last_idx = -1
            prev_idx = -2
            
            # Check for immediate continuity
            if years[last_idx] - years[prev_idx] > 2:
                status = "Sporadic"
            else:
                curr_ncf = ncf_values[last_idx]
                prev_ncf = ncf_values[prev_idx]
                
                # Growth definition: Change in NCF / Prev NCF
                # Adding small epsilon for stability
                growth_rate = (curr_ncf - prev_ncf) / max(prev_ncf, 0.001)
                
                if growth_rate > 0.5:
                    status = "Emerging"
                elif growth_rate < -0.3:
                    status = "Declining"
                elif total_count > 10 and abs(growth_rate) < 0.1:
                    status = "Saturated"
                else:
                    status = "Stable"
        elif len(years) == 1:
            status = "New"

        # 3. Stability (Variance of NCF)
        if len(ncf_values) < 2:
            stability = "Transient" # Too short to judge
        else:
            # Calculate variance of NCF
            try:
                variance = statistics.variance(ncf_values) if len(ncf_values) > 1 else 0
                # Heuristic thresholds for variance
                if variance > 0.05: # High fluctuation
                    stability = "Volatile"
                else:
                    stability = "Stable"
            except (ValueError, statistics.StatisticsError):
                stability = "Unknown"

        # 4. Confidence Score
        # Log-scaled Volume * (1 - Sparsity) * Validation
        # Sparsity: Missed years in range
        year_span = years[-1] - years[0] + 1
        active_years = len(years)
        sparsity = 1.0 - (active_years / max(1, year_span))
        
        # Validation boost: if it has relations or >1 paper
        is_valid = (total_count > 1) or has_relations
        validation_factor = 1.0 if is_valid else 0.5
        
        raw_conf = math.log1p(total_count) * 0.2 # Scale log(100) ~ 0.92
        confidence = raw_conf * (1.0 - (0.5 * sparsity)) * validation_factor
        confidence = min(1.0, max(0.1, confidence))

        # 5. Semantic Drift (Context Evolution)
        # Calculate overlap of neighbors in first vs last active year
        semantic_drift = "Unknown"
        if len(years) >= 2:
            first_year = years[0]
            last_year = years[-1]
            
            # Get neighbors (keys of the relations dict)
            neighbors_start = set(yearly_data[first_year]["relations"].keys())
            neighbors_end = set(yearly_data[last_year]["relations"].keys())
            
            if neighbors_start and neighbors_end:
                 # Jaccard index
                 union_size = len(neighbors_start | neighbors_end)
                 overlap = len(neighbors_start & neighbors_end) / max(1, union_size)
                 
                 if overlap < 0.3:
                     semantic_drift = "High"
                 elif overlap < 0.6:
                     semantic_drift = "Moderate"
                 else:
                     semantic_drift = "Low"
            elif neighbors_start or neighbors_end:
                 # One end is empty, explicit change in context availability
                 semantic_drift = "High" 
            else:
                 # No context in either, purely count based
                 semantic_drift = "Low"
        else:
             semantic_drift = "Low" # Only one year, no drift possible

        final_trends[concept] = {
            "status": status,
            "scope": scope,
            "stability": stability,
            "semantic_drift": semantic_drift,
            "is_trend_valid": is_valid,
            "growth_rate": round(growth_rate, 2),
            "trend_confidence": round(confidence, 2),
            "total_count": total_count,
            "trend_vector": trend_vector,
            "last_active_year": years[-1]
        }
        
    return {
        "metadata": {
            "window_used": {"start": start_year, "end": end_year}
        },
        "trends": final_trends
    }
