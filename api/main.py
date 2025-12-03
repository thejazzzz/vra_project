# File: api/main.py
import os
from contextlib import asynccontextmanager
import logging

from dotenv import load_dotenv

# Load .env.local ONLY when not in production (i.e., not in Docker)
if os.getenv("APP_ENV") != "production":
    load_dotenv(".env.local")

from fastapi import FastAPI
from database.db import init_db
from api.routers import health, planner, research, analysis, reporting

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting VRA Backend — initializing DB")
    init_db()
    yield
    logger.info("🛑 Shutting down VRA Backend")

app = FastAPI(
    title="VRA - Virtual Research Assistant API",
    version="1.0.0",
    description="Backend API for the Virtual Research Assistant (VRA).",
    lifespan=lifespan,
)


# Register routers
app.include_router(health.router)
app.include_router(planner.router, prefix="/planner", tags=["Planner Agent"])
app.include_router(research.router, prefix="/research", tags=["Research Agent"])
app.include_router(analysis.router, prefix="/analysis", tags=["Analysis Agent"])
app.include_router(reporting.router, prefix="/reporting", tags=["Reporting Agent"])


@app.get("/")
async def root():
    return {"message": "VRA Backend Running Successfully 🚀"}
