# api/main.py
from dotenv import load_dotenv
import os

# Load correct environment config
env = os.getenv("APP_ENV", "local")
if env == "local":
    load_dotenv(".env.local")
else:
    load_dotenv(".env")

print(f"🔧 Loaded environment: {env}")

from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from database.db import init_db
from api.routers import health, planner, research, analysis, reporting
from api.routers import graphs,graph_viewer

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting VRA Backend — initializing DB")
    try:
        init_db()
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}", exc_info=True)
        raise
    yield
    logger.info("🛑 Shutting down VRA Backend")


app = FastAPI(
    title="VRA - Virtual Research Assistant API",
    version="1.0.0",
    description="Backend API for the Virtual Research Assistant (VRA).",
    lifespan=lifespan
)


# Register routers
app.include_router(health.router)
app.include_router(planner.router, prefix="/planner", tags=["Planner Agent"])
app.include_router(research.router, prefix="/research", tags=["Research Agent"])
app.include_router(analysis.router, prefix="/analysis", tags=["Analysis Agent"])
app.include_router(reporting.router, prefix="/reporting", tags=["Reporting Agent"])
app.include_router(graphs.router, prefix="/graphs", tags=["Graphs"])
app.include_router(graph_viewer.router, prefix="/graph-viewer", tags=["Graph Viewer"])


@app.get("/")
async def root():
    return {"message": "VRA Backend Running Successfully 🚀"}
