# api/routers/research.py
from fastapi import APIRouter, HTTPException
from fastapi.exceptions import RequestValidationError
from api.models.research_models import ResearchRequest, ResearchResponse
from services.research_service import process_research_task
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=ResearchResponse)
async def research_endpoint(payload: ResearchRequest) -> ResearchResponse:
    try:
        result = await process_research_task(payload.query)

        # If pipeline failed internally
        if not result.get("success", False):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Pipeline processing failed")
            )
        return ResearchResponse(
            status="success",
            data=result
        )

    except RequestValidationError as e:
        logger.warning(f"Validation error in research_endpoint: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid request payload"
        )

    except Exception as e:
        logger.error("Error in research_endpoint", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
