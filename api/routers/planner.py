# File: api/routers/planner.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from api.models.research_models import ResearchRequest
from state.state_schema import VRAState
from services.state_service import load_state_for_query, save_state_for_query
from services.research_service import process_research_task
from agents.planner_agent import planner_agent
from copy import deepcopy
from database.db import SessionLocal
from workflow import run_step, run_until_interaction
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
def _load_or_create_state(query: str, user_id: str):
    state = load_state_for_query(query, user_id)
    if state:
        return state
    
    # Initialize minimal valid state
    return VRAState(
        query=query,
        collected_papers=[],
        selected_papers=[],
        added_papers=[],
        paper_summaries={},
        paper_concepts={},
        paper_relations={},
        global_analysis={},
        knowledge_graph={},
        citation_graph={},
        current_step=None,
        user_feedback=None,
        audience="general",
        user_id=user_id,
    )


from api.dependencies.auth import get_current_user, get_db
from database.models.auth_models import User, ResearchSession, SessionStatus
from sqlalchemy.orm import Session
from services.audit_service import log_action
import uuid
from typing import List, Dict
from datetime import datetime, timezone

def update_session_status(db: Session, session_id: str, current_step: str):
    """Updates the session status in the DB based on the workflow step."""
    new_status = SessionStatus.RUNNING
    if current_step == "completed":
        new_status = SessionStatus.COMPLETED
    elif current_step in ["failed", "error"]:
        new_status = SessionStatus.ERROR
    elif current_step and current_step.startswith("awaiting_"):
        new_status = SessionStatus.AWAITING_INPUT
    
    session = db.query(ResearchSession).filter(ResearchSession.session_id == session_id).first()
    if session:
        session.status = new_status
        session.last_updated = datetime.now(timezone.utc)
        db.commit()


class SessionSchema(BaseModel):
    session_id: str
    query: str
    status: str
    last_updated: datetime
    
    class Config:
        from_attributes = True

@router.post("/plan")
async def plan_task(payload: ResearchRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = (payload.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query required")

    # Generate unique Session ID (UUID)
    session_id = str(uuid.uuid4())
    user_id = current_user.id
    
    # Initialize state
    state = load_state_for_query(session_id, user_id)
    if not state:
        state = VRAState(
            query=query,
            user_id=user_id,
            collected_papers=[],
            selected_papers=[],
            added_papers=[],
            paper_summaries={},
            paper_concepts={},
            paper_relations={},
            global_analysis={},
            knowledge_graph={},
            citation_graph={},
            current_step=None,
            user_feedback=None,
            audience="industry",
        )
    
    # Create persistent session in DB
    session = ResearchSession(
        session_id=session_id, 
        user_id=user_id, 
        query=query,
        status=SessionStatus.RUNNING 
    )
    db.add(session)
    db.commit()


    # Save initial state using session_id as the key
    save_state_for_query(session_id, state, user_id)

    # Trigger research (using original query)
    if state.get("collected_papers"):
         return {"state": state, "session_id": session_id}

    try:
        result = await process_research_task(query)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail="Paper search failed")

        papers = result["papers"]

        # Ensure canonical_id exists
        for p in papers:
            if "canonical_id" not in p:
                logger.error(f"Paper missing canonical_id: {p}")
                raise HTTPException(status_code=500, detail="Paper missing canonical_id")

        state["collected_papers"] = papers
        state["selected_papers"] = deepcopy(papers)
        state["current_step"] = "awaiting_research_review"
        state["audience"] = payload.audience or "industry"
        save_state_for_query(session_id, state, user_id)
        return {"state": state, "session_id": session_id}

    except HTTPException:
        # Update status on error
        update_session_status(db, session_id, "failed")
        raise
    except Exception:
        logger.error("Research task failed", exc_info=True)
        update_session_status(db, session_id, "failed")
        raise HTTPException(status_code=500, detail="Paper search failed")


@router.post("/continue/{session_id}")
async def continue_workflow(
    session_id: str, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")

    user_id = current_user.id
    
    # Ownership Check
    session = db.query(ResearchSession).filter(ResearchSession.session_id == session_id).first()
    if not session or session.user_id != user_id:
        raise HTTPException(403, "Forbidden: session does not belong to user")

    state = load_state_for_query(session_id, user_id)
    if not state:
         raise HTTPException(404, "State not found")

    state["user_id"] = user_id # Ensure user_id is present for legacy states

    if not state.get("collected_papers"):
        raise HTTPException(
            status_code=400,
            detail="No state initialized. Call /plan first."
        )

    try:
        updated = await run_until_interaction(state)
        save_state_for_query(session_id, updated, user_id)
        
        # Update DB status
        update_session_status(db, session_id, updated.get("current_step"))
        
        return {"state": updated}

    except Exception as e:
        logger.error("Workflow continuation failed", exc_info=True)
        update_session_status(db, session_id, "failed")
        raise HTTPException(
            status_code=500,
            detail=f"Workflow execution failed: {str(e)}"
        )


class PaperReviewRequest(BaseModel):
    query: str
    selected_paper_ids: list[str]
    audience: str = "industry"


@router.post("/review")
async def review_papers(
    payload: PaperReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # The payload.query field now holds the session_id (UUID)
    session_id = (payload.query or "").strip() 
    user_id = current_user.id
    
    # DB Ownership Check
    session = db.query(ResearchSession).filter(ResearchSession.session_id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")
    if session.user_id != user_id:
        raise HTTPException(403, "Forbidden: session does not belong to user")

    state = load_state_for_query(session_id, user_id)
    if not state:
         raise HTTPException(404, "State not found")
         
    state["user_id"] = user_id # Ensure user_id is set

    if not state.get("collected_papers"):
        raise HTTPException(400, "No collected papers to review")

    # Filter papers
    selected_ids = set(payload.selected_paper_ids)
    all_papers = state.get("collected_papers", [])

    # Keep only selected papers in the active set
    # We still keep 'collected_papers' as history if needed, but 'selected_papers' drives the next steps
    final_selection = [p for p in all_papers if p.get("canonical_id") in selected_ids]

    if not final_selection:
        raise HTTPException(400, "No papers selected. Cannot proceed.")

    state["selected_papers"] = final_selection
    state["audience"] = payload.audience or "industry"

    # Trigger next step: Analysis
    # We manually set the transition here because this IS the user interaction
    state["current_step"] = "awaiting_analysis"

    # Save immediately
    save_state_for_query(session_id, state, user_id)

    # Audit Log
    log_action(
        db, 
        user_id=user_id, 
        action="REVIEW_PAPERS", 
        target_id=session_id, 
        payload={"selected_count": len(final_selection)}
    )

    # Run loop
    try:
        updated = await run_until_interaction(state)
        save_state_for_query(session_id, updated, user_id)
        
        update_session_status(db, session_id, updated.get("current_step"))
        
        return {"state": updated}
    except Exception as e:
        logger.error("Review processing failed", exc_info=True)
        update_session_status(db, session_id, "failed")
        raise HTTPException(500, f"Failed to process review: {e}")


class GraphReviewRequest(BaseModel):
    query: str
    feedback: str = None
    approved: bool = True


@router.post("/review-graph")
async def review_graph(
    payload: GraphReviewRequest, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # The payload.query field is the session_id
    session_id = (payload.query or "").strip()
    if not session_id:
        raise HTTPException(400, "Session ID required")

    user_id = current_user.id
    
    # Ownership Check
    state = load_state_for_query(session_id, user_id)
    # If state not found, we fail. We DO NOT create new state here.
    if not state:
         logger.error(f"State not found for session_id={session_id} user_id={user_id}")
         raise HTTPException(404, "State not found")

    state["user_id"] = user_id # Ensure user_id is set
    # User requested verifying state ownership ID too, but let's stick to DB check first?
    
    # Check DB ownership explicitly as well or relying on state loading by user_id?
    # services/state_service.py filters by user_id. So if it loads, it's owned.
    # BUT explicitly checking matching IDs is safer.
    if not state:
         raise HTTPException(404, "State not found")
         
    # Check session record
    # Note: Using 'db' dependency injected earlier
    # Wait, the user instruction was "verify that the state/session is actually owned by current_user... if the state's owner id... does not match".
    # Since VRAState schema doesn't strictly have owner_id, we rely on the DB session check.
    
    session_record = db.query(ResearchSession).filter(ResearchSession.session_id == session_id).first()
    if not session_record:
         raise HTTPException(404, "Session not found in DB")

    if session_record.user_id != user_id:
        logger.error(f"Ownership mismatch: Session {session_id} owned by {session_record.user_id}, requested by {user_id}")
        raise HTTPException(403, "Forbidden: session does not belong to current user")
    
    # Validation: Ensure we are in the right state
    if state.get("current_step") != "awaiting_graph_review":
        # Strict check or lenient? Lenient allows recovery. 
        # But let's log warning.
        logger.warning(f"Graph review received but state is {state.get('current_step')}")

    # Set next step
    # We move to Gap Analysis (Level 4) or Reporting (Level 5)
    # Workflow.py says: awaiting_gap_analysis
    state["current_step"] = "awaiting_gap_analysis"
    if payload.feedback:
        state["user_feedback"] = payload.feedback

    save_state_for_query(session_id, state, user_id)

    # Audit Log
    log_action(
        db,
        user_id=user_id,
        action="REVIEW_GRAPH",
        target_id=session_id,
        payload={"approved": payload.approved, "feedback": payload.feedback}
    )

    try:
        updated = await run_until_interaction(state)
        save_state_for_query(session_id, updated, user_id)
        
        update_session_status(db, session_id, updated.get("current_step"))
        
        return {"state": updated}
    except Exception as e:
        logger.error("Graph review continuation failed", exc_info=True)
        update_session_status(db, session_id, "failed")
        raise HTTPException(500, f"Workflow failed: {e}")


@router.get("/status/{session_id}")
def get_status(
    session_id: str, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current status of the research task for polling.
    """
    user_id = current_user.id
    
    # Explicit ownership check
    session = db.query(ResearchSession).filter(ResearchSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Use read-only loader
    state_obj = load_state_for_query(session_id, user_id)
    
    if not state_obj:
        raise HTTPException(status_code=404, detail="State not found")
        
    return {"state": state_obj}


@router.get("/sessions", response_model=Dict[str, List[SessionSchema]])
def get_user_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    List all research sessions for the authenticated user.
    """
    sessions = db.query(ResearchSession)\
        .filter(ResearchSession.user_id == current_user.id)\
        .order_by(ResearchSession.last_updated.desc())\
        .all()
    return {"sessions": sessions}

