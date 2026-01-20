# database/models/evaluation_model.py
from sqlalchemy import Column, Integer, String, JSON, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from database.db import Base

class GoldStandard(Base):
    """
    Phase 4: Evaluation Ground Truth.
    Manual or curated triplets to validate KGs against.
    """
    __tablename__ = "gold_standards"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    query = Column(String(500), nullable=False, index=True)
    
    # Triplet
    subject = Column(String(255), nullable=False)
    predicate = Column(String(255), nullable=False) # e.g. "improves"
    object = Column(String(255), nullable=False)
    
    source = Column(String(100), default="manual") # manual, synthetic, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EvaluationRun(Base):
    """
    Phase 4: Quantitative Metrics Log.
    Tracks system performance over time.
    """
    __tablename__ = "evaluation_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(String(100), nullable=False, index=True) # Corresponds to KG run_meta ID
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Metadata
    model_version = Column(String(100))
    query = Column(String(500))
    
    # Metrics
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    
    # Calibration Metrics (JSON)
    # e.g. {"confidence_bin_0.8": 0.9, "calibration_error": 0.12}
    calibration_metrics = Column(JSON, nullable=True) 
    
    # Detailed Errors (JSON)
    # e.g. {"false_positives": [...], "false_negatives": [...]}
    details = Column(JSON, nullable=True)
