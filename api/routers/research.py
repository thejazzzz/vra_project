# File: api/routers/research.py
from fastapi import APIRouter, HTTPException
from api.models.research_models import ResearchRequest, ResearchResponse
from services.research_service import process_research_task

router = APIRouter()

@router.post("/", response_model=ResearchResponse)
async def research_endpoint(payload: ResearchRequest):
    try:
        result = await process_research_task(payload.query)
        return ResearchResponse(status="success", data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


