# File: api/routers/analysis.py
from fastapi import APIRouter, HTTPException
from api.models.analysis_models import AnalysisRequest, AnalysisResponse
from services.analysis_service import run_analysis_task
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/run", response_model=AnalysisResponse)
async def run_analysis(payload: AnalysisRequest) -> AnalysisResponse:
    try:
        if not payload.query or not payload.query.strip():
            raise ValueError("Query cannot be empty")

        data = await run_analysis_task(payload.query, payload.papers)
        return AnalysisResponse(status="success", data=data)

    except ValueError as e:
        logger.warning(f"Validation error in run_analysis: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error("Unexpected error in run_analysis", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred")
