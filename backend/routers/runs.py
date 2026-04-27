"""
Endpoints for executing LLM queries (runs).
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from db import Prompt, Result, Run, SessionLocal, get_db

logger = logging.getLogger(__name__)
from llm.providers import UnifiedLLMClient
from llm.runner import QueryRunner
from models.schemas import RunCreate, RunProgress, RunResponse

router = APIRouter()

# Registry of run_id -> QueryRunner for cancel. Cleared when run finishes.
_active_runners: dict[str, QueryRunner] = {}


def _load_prompts_for_run(db: Session, project_id: str) -> list[dict]:
    """Load all prompts for the project (including generated variants). Ensure each prompt_id has baseline 'standard' variant."""
    from db import Project

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return []
    rows = db.query(Prompt).filter(Prompt.project_id == project_id).order_by(Prompt.prompt_id, Prompt.id).all()
    if not rows:
        return []
    # Require each prompt_id to have at least one "standard" variant
    prompt_ids_with_standard = {p.prompt_id for p in rows if p.variant == "standard"}
    prompt_ids_all = {p.prompt_id for p in rows}
    missing = prompt_ids_all - prompt_ids_with_standard
    if missing:
        # Only include prompt_ids that have a standard variant
        rows = [p for p in rows if p.prompt_id in prompt_ids_with_standard]
    return [{"id": p.id, "prompt_text": p.prompt_text} for p in rows]


def _progress_payload(db: Session, run: Run) -> dict[str, Any]:
    total = run.total_prompts or 0
    completed = run.completed_prompts or 0
    progress_pct = (completed / total * 100.0) if total else 0.0
    return {
        "run_id": run.id,
        "status": run.status,
        "total_prompts": total,
        "completed_prompts": completed,
        "error_count": run.error_count or 0,
        "progress_pct": round(progress_pct, 2),
        "eta_seconds": None,
        "message": getattr(run, "progress_message", None),
    }


def _normalize_api_key(api_key: str | None) -> str | None:
    """Use None when key is missing or blank so LLM client can fall back to env (e.g. OPENAI_API_KEY)."""
    if api_key is None:
        return None
    key = (api_key or "").strip()
    return key if key else None


# Env vars used by LiteLLM when api_key is not passed (see litellm docs)
_PROVIDER_ENV_KEYS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GOOGLE_API_KEY",
}


def _require_api_key(provider: str, api_key: str | None) -> None:
    """Raise HTTPException 400 if provider needs an API key and none is set (in request or env)."""
    if provider not in _PROVIDER_ENV_KEYS:
        return
    key = _normalize_api_key(api_key)
    if key:
        return
    env_var = _PROVIDER_ENV_KEYS[provider]
    if os.environ.get(env_var):
        return
    raise HTTPException(
        status_code=400,
        detail=f"API key required for {provider}. Enter it in the API Key field above, or set {env_var} on the server.",
    )


async def _execute_run_background(
    run_id: str,
    project_id: str,
    task_modality: str,
    model_provider: str,
    model_id: str,
    api_key: str | None,
    base_url: str | None,
    system_prompt: str,
    temperature: float,
    max_tokens: int,
) -> None:
    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        if run and hasattr(run, "progress_message"):
            run.progress_message = "Starting..."
            db.commit()

        client = UnifiedLLMClient(
            provider=model_provider,
            model=model_id,
            api_key=_normalize_api_key(api_key),
            base_url=(base_url or "").strip() or None,
        )
        runner = QueryRunner(client, db, run_id, task_modality=task_modality)
        _active_runners[run_id] = runner
        prompts = _load_prompts_for_run(db, project_id)
        await runner.execute_run(
            prompts=prompts,
            system_prompt=system_prompt or "",
            temperature=temperature or 0.0,
            max_tokens=max_tokens or 150,
        )
    except Exception as e:
        logger.exception("Run failed: run_id=%s", run_id)
        run = db.query(Run).filter(Run.id == run_id).first()
        if run and run.status == "running":
            run.status = "failed"
            run.completed_at = datetime.utcnow()
            msg = str(e)
            if hasattr(run, "progress_message"):
                run.progress_message = msg[:2000] if len(msg) > 2000 else msg
            db.commit()
    finally:
        _active_runners.pop(run_id, None)
        db.close()


@router.get("/models")
def get_models():
    """Return list of supported models with provider prefixes."""
    return UnifiedLLMClient.get_supported_models()


@router.post("/create", response_model=RunResponse, status_code=201)
async def create_run(data: RunCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Create a run, start QueryRunner in background, return run_id and status=running."""
    from db import Project

    project = db.query(Project).filter(Project.id == data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    prompts_list = _load_prompts_for_run(db, data.project_id)
    total_prompts = len(prompts_list)
    if total_prompts == 0:
        raise HTTPException(status_code=400, detail="Project has no prompts (or no prompt_id has baseline 'standard' variant)")

    _require_api_key(data.model_provider, data.api_key)

    run_id = str(uuid.uuid4())
    run = Run(
        id=run_id,
        project_id=data.project_id,
        model_provider=data.model_provider,
        model_id=data.model_id,
        system_prompt=data.system_prompt,
        temperature=data.temperature,
        status="running",
        total_prompts=total_prompts,
        completed_prompts=0,
        error_count=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    logger.info("Run created: run_id=%s project_id=%s total_prompts=%s", run_id, data.project_id, total_prompts)

    background_tasks.add_task(
        _execute_run_background,
        run_id=run_id,
        project_id=data.project_id,
        task_modality=project.task_modality,
        model_provider=data.model_provider,
        model_id=data.model_id,
        api_key=_normalize_api_key(data.api_key),
        base_url=data.base_url,
        system_prompt=data.system_prompt or "",
        temperature=data.temperature if data.temperature is not None else 0.0,
        max_tokens=data.max_tokens if data.max_tokens is not None else 150,
    )

    return RunResponse(
        id=run.id,
        project_id=run.project_id,
        model_provider=run.model_provider,
        model_id=run.model_id,
        system_prompt=run.system_prompt,
        temperature=run.temperature,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        total_prompts=run.total_prompts,
        completed_prompts=run.completed_prompts,
        error_count=run.error_count,
    )


@router.get("/{run_id}/progress", response_model=RunProgress)
def get_run_progress(run_id: str, db: Session = Depends(get_db)):
    """Return current progress of a run."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        logger.warning("Run not found: %s", run_id)
        raise HTTPException(status_code=404, detail="Run not found")
    payload = _progress_payload(db, run)
    return RunProgress(**payload)


@router.get("/{run_id}/progress/stream")
async def stream_run_progress(run_id: str, db: Session = Depends(get_db)):
    """SSE stream of progress updates every 2 seconds until run completes or errors."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator():
        while True:
            # Use a fresh session each poll so we see latest committed data from the background runner
            poll_db = SessionLocal()
            try:
                run = poll_db.query(Run).filter(Run.id == run_id).first()
                if not run:
                    yield ServerSentEvent(data=json.dumps({"error": "Run not found"}), event="error")
                    return
                payload = _progress_payload(poll_db, run)
                yield ServerSentEvent(
                    data=json.dumps(payload),
                    event="progress",
                )
                if run.status in ("completed", "cancelled", "failed"):
                    yield ServerSentEvent(data=json.dumps(payload), event="complete")
                    return
            finally:
                poll_db.close()
            await asyncio.sleep(2)

    return EventSourceResponse(event_generator())


@router.post("/{run_id}/cancel")
def cancel_run(run_id: str, db: Session = Depends(get_db)):
    """Set runner cancelled flag and update run status to cancelled."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        logger.warning("Cancel run not found: %s", run_id)
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "running":
        logger.info("Cancel run ignored (not running): run_id=%s status=%s", run_id, run.status)
        return {"run_id": run_id, "status": run.status, "message": "Run is not running"}
    runner = _active_runners.get(run_id)
    if runner:
        runner.cancel()
    run.status = "cancelled"
    run.completed_at = datetime.utcnow()
    db.commit()
    logger.info("Run cancelled: run_id=%s", run_id)
    return {"run_id": run_id, "status": "cancelled"}


@router.get("/project/{project_id}")
def list_runs_for_project(project_id: str, db: Session = Depends(get_db)):
    """Return list of all runs for a project with their status."""
    from db import Project

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    runs = db.query(Run).filter(Run.project_id == project_id).order_by(Run.started_at.desc()).all()
    return [
        {
            "id": r.id,
            "project_id": r.project_id,
            "model_provider": r.model_provider,
            "model_id": r.model_id,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "total_prompts": r.total_prompts,
            "completed_prompts": r.completed_prompts,
            "error_count": r.error_count,
        }
        for r in runs
    ]
