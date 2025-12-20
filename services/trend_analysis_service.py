# services/trend_analysis_service.py
from collections import defaultdict
from typing import List, Dict, Any

def detect_concept_trends(papers: List[Dict[str, Any]], concepts_per_paper: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Detects temporal trends, calculates growth rates, and assigns status.
    Phase 3.1 Enhanced: Saturation Status & Confidence Metric.
    """
    trends = defaultdict(lambda: {"years": defaultdict(int), "total": 0})
    
    for paper in papers:
        # Get ID and Year
        pid = paper.get("canonical_id")
        year = paper.get("year") or paper.get("publication_year") or paper.get("published_year")
        
        if not pid or not year:
            continue

        # Validate year is numeric
        try:
            year_int = int(year)
        except (ValueError, TypeError):
            continue
            
        categories = concepts_per_paper.get(pid, [])
        for concept in categories:
            c_norm = concept.lower().strip()
            trends[c_norm]["years"][str(year_int)] += 1
            trends[c_norm]["total"] += 1
            
    final_trends = {}
    
    for concept, data in trends.items():
        years = sorted(data["years"].keys(), key=int)
        counts_by_year = dict(data["years"])
        total = data["total"]
        
        growth_rate = 0.0
        status = "stable"
        
        if len(years) >= 2:
            last_year = years[-1]
            prev_year = years[-2]
            
            # Check for sparse data (Gap > 2 years)
            if int(last_year) - int(prev_year) > 2:
                status = "sporadic"
            else:
                recent_count = counts_by_year[last_year]
                prev_count = counts_by_year[prev_year]
                
                # Simple YoY growth
                growth_rate = (recent_count - prev_count) / max(prev_count, 1)
                
                if growth_rate > 0.5:
                    status = "emerging"
                elif growth_rate < -0.3:
                    status = "declining"
                else:
                    status = "stable"
                
                # Enhanced: Saturation Check
                if total > 10 and status == "stable":
                    status = "saturated"
                
        elif len(years) == 1:
            status = "new"

        # Enhanced: Trend Confidence
        # Simple heuristic: more data = more confidence
        trend_confidence = min(1.0, total / 10.0)

        final_trends[concept] = {
            "counts_by_year": counts_by_year,
            "total_count": total,
            "growth_rate": round(growth_rate, 2),
            "status": status,
            "trend_confidence": round(trend_confidence, 2),
            "last_active_year": years[-1] if years else None
        }
        
    return final_trends
