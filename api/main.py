# File: api/main.py
from fastapi import FastAPI
from api.routers import health, planner, research, analysis, reporting

app = FastAPI(
    title="VRA - Virtual Research Assistant API",
    version="1.0.0",
    description="Backend API for the Virtual Research Assistant (VRA)."
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


