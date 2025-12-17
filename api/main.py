# api/main.py
from dotenv import load_dotenv
import os

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
from fastapi.middleware.cors import CORSMiddleware

from api.routers import (
    health,
    planner,
    research,
    analysis,
    reporting,
    graphs,
    graph_viewer,
)

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

# CORS Configuration
origins = []
if env == "local":
    origins = ["http://localhost:3000", "http://localhost:5173"]  # Common dev ports
else:
    # Production origins from environment variable
    origins_str = os.getenv("ALLOWED_ORIGINS", "")
    origins = [origin.strip() for origin in origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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
