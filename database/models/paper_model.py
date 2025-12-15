# database/models/paper_model.py
from sqlalchemy import Column, Integer, String, Text, JSON
from database.db import Base


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Original IDs from sources (optional, for back-compat)
    paper_id = Column(String(255), unique=True, nullable=True)

    # REQUIRED canonical ID
    canonical_id = Column(String(255), unique=True, index=True, nullable=False)

    # Core metadata
    title = Column(String(512), nullable=False)
    abstract = Column(Text, nullable=True)
    raw_text = Column(Text, nullable=True)

    # Multi-source metadata
    paper_metadata = Column(JSON, default=lambda: {})

    # Optional structured/normalized metadata
    published_year = Column(Integer, nullable=True)
    doi = Column(String(255), nullable=True)
    arxiv_id = Column(String(255), nullable=True)
    semantic_scholar_id = Column(String(255), nullable=True)
