import traceback

try:
    from dotenv import load_dotenv
    import os
    load_dotenv()
    os.environ["POSTGRES_HOST"] = "localhost"
    from database.db import SessionLocal
    from database.models.workflow_state_model import WorkflowState
    db = SessionLocal()
    latest = db.query(WorkflowState).order_by(WorkflowState.id.desc()).first()
    if latest:
        out = str(latest.state.get("error"))
    else:
        out = "No state records found."
    with open("inspect_output.txt", "w", encoding="utf-8") as f:
        f.write(out)
except Exception as e:
    with open("inspect_output.txt", "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())
