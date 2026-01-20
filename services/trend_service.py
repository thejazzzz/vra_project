# services/trend_service.py
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from database.models.memory_model import TrendState

class TrendService:
    """
    Phase 4: Trend Classification Logic.
    Determines if a concept is Emerging, Stable, Declining, or Re-emerging.
    """
    
    @staticmethod
    def calculate_trend(first_seen: datetime, last_seen: datetime, _run_count: int, weighted_freq: float) -> TrendState:
        now = datetime.now(timezone.utc)
        
        # Age of knowledge
        age = now - first_seen
        recency = now - last_seen
        
        # 1. DECLINING / STAGNANT
        # Rule: Not seen in 1 year
        if recency > timedelta(days=365):
            return TrendState.DECLINING

        # 2. STABLE
        # Rule: Known for > 6 months AND High Weighted Frequency (> 5.0)
        # Prioritized over Re-emerging to catch consistent long-term topics
        if age > timedelta(days=180) and weighted_freq > 5.0:
            return TrendState.STABLE
        
        # 3. REEMERGING: Old concept revived recently
        # Rule: First seen > 2 years ago, BUT active in last 30 days
        if age > timedelta(days=730) and recency < timedelta(days=30):
            return TrendState.REEMERGING
            
        # 4. EMERGING (Default for new)
        # Fallback for any content < 6 months old or failing other criteria.
        return TrendState.EMERGING
