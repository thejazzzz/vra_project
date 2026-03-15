# database/db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import quote_plus

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DB_USER = os.getenv("POSTGRES_USER")
    DB_PASS = os.getenv("POSTGRES_PASSWORD")
    DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
    DB_PORT = os.getenv("POSTGRES_PORT", "5432")
    DB_NAME = os.getenv("POSTGRES_DB")
    
    if not all([DB_USER, DB_PASS, DB_NAME]):
        raise ValueError("Database credentials must be provided via DATABASE_URL or POSTGRES_* environment variables")
    
    DATABASE_URL = (
        f"postgresql://{quote_plus(DB_USER)}:{quote_plus(DB_PASS)}@"
        f"{DB_HOST}:{DB_PORT}/{quote_plus(DB_NAME)}"
    )
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_pre_ping=True,
    future=True,    # Recommended for SQLAlchemy 2.x
    connect_args={"connect_timeout": 10},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def init_db():
    # Import all models so tables are created
    from database.models.paper_model import Paper
    from database.models.workflow_state_model import WorkflowState
    from database.models.graph_model import Graph  # <-- REQUIRED
    from database.models.auth_models import User, ResearchSession, AuditLog

    Base.metadata.create_all(bind=engine)

    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            # Check if column exists, if not add it
            conn.execute(text("ALTER TABLE graphs ADD COLUMN IF NOT EXISTS session_id VARCHAR(255)"))
            
            # Create index, IF NOT EXISTS is standard but depends on Postgres version, so we catch error
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_graphs_session_id ON graphs(session_id)"))
            except Exception:
                pass
                
            print("✅ Database migration applied successfully: session_id verified on graphs")
    except Exception as e:
        print(f"⚠️ Database migration info: {e}")
