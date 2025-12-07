# File: database/models/paper_model.py
from sqlalchemy import Column, Integer, String, Text, JSON
from database.db import Base

class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    paper_id = Column(String(255), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    abstract = Column(Text)
    raw_text = Column(Text, nullable=True)  # full text later
    paper_metadata = Column(JSON, default=lambda: {})
