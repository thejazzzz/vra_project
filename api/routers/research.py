# File: api/routers/research.py
from fastapi import APIRouter, HTTPException
from api.models.research_models import ResearchRequest, ResearchResponse
from services.research_service import process_research_task
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=ResearchResponse)
async def research_endpoint(payload: ResearchRequest) -> ResearchResponse:
    try:
        result = await process_research_task(payload.query)
        return ResearchResponse(status="success", data=result)
    except ValueError as e:
        logger.warning(f"Validation error in research_endpoint: {e}")
        raise HTTPException(status_code=400, detail="Invalid request")
    except Exception as e:
        logger.error("Error in research_endpoint", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred"
        )
