# services/memory_service.py
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from database.db import SessionLocal
from database.models.memory_model import GlobalConceptStats, GlobalEdgeStats, TrendState
from services.trend_service import TrendService

logger = logging.getLogger(__name__)

class MemoryService:
    """
    Phase 4: Global Research Memory.
    Manages longitudinal tracking of concepts/edges across runs.
    Enforces Approval-Gated updates.
    """
    
    @staticmethod
    def update_global_stats(kg_data: Dict, approved: bool = False):
        """
        Update global stats with new graph data.
        CRITICAL: Only updates if `approved=True`. Unverified runs are ignored.
        """
        if not approved:
            logger.info("Memory update skipped (Graph not approved).")
            return

        nodes = kg_data.get("nodes", [])
        links = kg_data.get("links", [])
        
        # Only process concepts, not papers
        concepts = [n for n in nodes if n.get("type", "concept") == "concept"]
        
        with SessionLocal() as db:
            MemoryService._upsert_concepts(db, concepts)
            MemoryService._upsert_edges(db, links)
            db.commit()
            logger.info("✅ Global Memory updated (Approved Run).")

    @staticmethod
    def _upsert_concepts(db: Session, concepts: List[Dict]):
        now = datetime.now(timezone.utc)
        for c in concepts:
            c_id = c.get("id")
            if not c_id: continue
            
            stat = db.scalar(select(GlobalConceptStats).where(GlobalConceptStats.concept_id == c_id))
            
            if not stat:
                stat = GlobalConceptStats(
                    concept_id=c_id, 
                    first_seen=now, 
                    last_seen=now,
                    run_count=1,
                    weighted_frequency=1.0, # Base
                    trend_state=TrendState.EMERGING # Init
                )
                db.add(stat)
            else:
                stat.last_seen = now
                stat.run_count += 1
                stat.weighted_frequency += 1.0 
                
                # Trend Logic
                stat.trend_state = TrendService.calculate_trend(
                    stat.first_seen, 
                    stat.last_seen, 
                    stat.run_count, 
                    stat.weighted_frequency
                )

    @staticmethod
    def _upsert_edges(db: Session, links: List[Dict]):
        now = datetime.now(timezone.utc)
        for l in links:
            s, t = l["source"], l["target"]
            rel = l.get("relation", "related_to")
            conf = l.get("confidence", 0.5)
            
            # Skip meta
            if rel == "appears_in": continue
            
            stat = db.scalar(
                select(GlobalEdgeStats).where(
                    GlobalEdgeStats.source == s,
                    GlobalEdgeStats.target == t,
                    GlobalEdgeStats.relation == rel
                )
            )
            
            if not stat:
                stat = GlobalEdgeStats(
                    source=s, target=t, relation=rel,
                    first_seen=now, last_seen=now,
                    run_count=1,
                    weighted_frequency=conf
                )
                db.add(stat)
            else:
                stat.last_seen = now
                stat.run_count += 1
                stat.weighted_frequency += conf # Weighted by confidence

    @staticmethod
    def mark_contested(source: str, target: str, user_id: str):
        """
        Record user disagreement without destroying history.
        """
        with SessionLocal() as db:
            # Find all edges between s and t (relation agnostic or specific?)
            # Usually users reject the *link*, regardless of relation nuances.
            stats = db.scalars(
                select(GlobalEdgeStats).where(
                    GlobalEdgeStats.source == source,
                    GlobalEdgeStats.target == target
                )
            ).all()
            
            for stat in stats:
                stat.contested_count += 1
                current_users = list(stat.contested_by_users) if stat.contested_by_users else []
                if user_id not in current_users:
                    current_users.append(user_id)
                    stat.contested_by_users = current_users
            
            db.commit()
            logger.info(f"Marked edge {source}->{target} as contested by {user_id}")
    
    @staticmethod
    def get_edge_context(source: str, target: str) -> Dict:
        """
        Retrieve historical context for Novelty Scoring.
        """
        with SessionLocal() as db:
            stats = db.scalars(
                select(GlobalEdgeStats).where(
                    GlobalEdgeStats.source == source,
                    GlobalEdgeStats.target == target
                )
            ).all()
            
            if not stats: return {}
            
            # Aggregate if multiple relations
            total_runs = max(s.run_count for s in stats)
            total_contested = sum(s.contested_count for s in stats)
            
            return {
                "max_run_count": total_runs,
                "is_contested": total_contested > 0,
                "contested_count": total_contested
            }
