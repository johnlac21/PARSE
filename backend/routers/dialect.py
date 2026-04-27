"""
Dialect router: available dialects, test connection, rewrite preview, and background generation.
"""

import time
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db import SessionLocal, get_db, Prompt, Project
from engine.dialect.config import AVAILABLE_DIALECTS
from engine.dialect.llm_rewriter import SimpleRewriter, ConstrainedRewriter
from llm.providers import UnifiedLLMClient

router = APIRouter()

# In-memory progress for dialect generation jobs: job_id -> {status, total_prompts, completed_prompts, dialects, error_count, message}
_dialect_jobs: dict[str, dict[str, Any]] = {}


# --- Request/Response schemas ---


class DialectMetadata(BaseModel):
    """Dialect metadata (no system prompt)."""
    id: str
    name: str
    type: str
    requires_llm: bool
    example_input: str
    example_output: str


class TestConnectionRequest(BaseModel):
    provider: str
    api_key: str
    model: str
    base_url: str | None = None


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    latency_ms: int


class RewritePreviewRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=3)
    dialect_ids: list[str]
    provider: str
    api_key: str
    model: str
    base_url: str | None = None
    constrained: bool = False
    parameter_columns: list[str] | None = None
    parameter_values: dict[str, list[str]] | None = None


class RewritePreviewItem(BaseModel):
    original: str
    dialect: str
    rewritten: str
    success: bool


class RewritePreviewResponse(BaseModel):
    results: list[RewritePreviewItem]


class GenerateRequest(BaseModel):
    project_id: str
    dialect_ids: list[str]
    provider: str
    api_key: str
    model: str
    base_url: str | None = None
    constrained: bool = False
    parameter_columns: list[str] | None = None


class GenerateResponse(BaseModel):
    job_id: str
    status: str = "started"
    total_prompts: int
    dialects: list[str]


class GenerateProgressResponse(BaseModel):
    job_id: str
    status: str
    total_prompts: int
    completed_prompts: int
    error_count: int
    progress_pct: float
    dialects: list[str]
    message: str | None = None


def _get_dialect_metadata() -> list[DialectMetadata]:
    """Build list of dialect metadata without exposing system prompts."""
    out = []
    for did, cfg in AVAILABLE_DIALECTS.items():
        out.append(DialectMetadata(
            id=cfg["id"],
            name=cfg["name"],
            type=cfg["type"],
            requires_llm=cfg.get("requires_llm", True),
            example_input=cfg.get("example_input", ""),
            example_output=cfg.get("example_output", ""),
        ))
    return out


def _client(provider: str, model: str, api_key: str, base_url: str | None) -> UnifiedLLMClient:
    return UnifiedLLMClient(provider=provider, model=model, api_key=api_key, base_url=base_url)


@router.get("/available", response_model=list[DialectMetadata])
def get_available_dialects():
    """Return all available dialects with metadata (no system prompts)."""
    return _get_dialect_metadata()


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_connection(body: TestConnectionRequest):
    """Make a simple test call to verify the API key works."""
    client = _client(body.provider, body.model, body.api_key, body.base_url)
    start = time.perf_counter()
    result = await client.query(
        prompt="Say hello in 5 words",
        system_prompt="",
        temperature=0,
        max_tokens=20,
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    if result.get("error"):
        return TestConnectionResponse(
            success=False,
            message=result["error"],
            latency_ms=latency_ms,
        )
    return TestConnectionResponse(
        success=True,
        message=result.get("raw_response", "").strip() or "OK",
        latency_ms=latency_ms,
    )


@router.post("/rewrite-preview", response_model=RewritePreviewResponse)
async def rewrite_preview(body: RewritePreviewRequest):
    """Run rewriting on sample texts and return previews."""
    for did in body.dialect_ids:
        if did not in AVAILABLE_DIALECTS:
            raise HTTPException(status_code=400, detail=f"Unknown dialect: {did}")
    client = _client(body.provider, body.model, body.api_key, body.base_url)
    results: list[RewritePreviewItem] = []

    if body.constrained and body.parameter_columns and body.parameter_values:
        rewriter = ConstrainedRewriter(client)
        # Build minimal prompt dicts from texts and parameter_values (align by index)
        prompts: list[dict] = []
        for i, text in enumerate(body.texts):
            row: dict[str, Any] = {"text": text}
            for col in body.parameter_columns or []:
                vals = (body.parameter_values or {}).get(col, [])
                row[col] = vals[i] if i < len(vals) else ""
            prompts.append(row)
        for dialect_id in body.dialect_ids:
            batch = await rewriter.rewrite_batch_constrained(
                prompts, body.parameter_columns or [], dialect_id, max_concurrent=3
            )
            for r in batch:
                results.append(RewritePreviewItem(
                    original=r["original"],
                    dialect=r["dialect"],
                    rewritten=r.get("rewritten", ""),
                    success=r.get("success", False),
                ))
    else:
        rewriter = SimpleRewriter(client)
        for text in body.texts:
            for dialect_id in body.dialect_ids:
                r = await rewriter.rewrite(text, dialect_id)
                results.append(RewritePreviewItem(
                    original=r["original"],
                    dialect=r["dialect"],
                    rewritten=r.get("rewritten", ""),
                    success=r.get("success", False),
                ))
    return RewritePreviewResponse(results=results)


async def _run_dialect_generation(
    job_id: str,
    project_id: str,
    dialect_ids: list[str],
    provider: str,
    api_key: str,
    model: str,
    base_url: str | None,
    constrained: bool,
    parameter_columns: list[str] | None,
) -> None:
    db = SessionLocal()
    try:
        job = _dialect_jobs.get(job_id)
        if not job:
            return
        job["status"] = "running"
        client = _client(provider, model, api_key, base_url)
        prompts = (
            db.query(Prompt)
            .filter(Prompt.project_id == project_id)
            .order_by(Prompt.id)
            .all()
        )
        total = len(prompts) * len(dialect_ids)
        completed = 0
        error_count = 0

        for dialect_id in dialect_ids:
            if dialect_id not in AVAILABLE_DIALECTS:
                job["message"] = f"Unknown dialect: {dialect_id}"
                job["status"] = "failed"
                return
            if constrained and parameter_columns:
                rewriter = ConstrainedRewriter(client)
                prompt_dicts = [
                    {"text": p.prompt_text, **(getattr(p, "metadata_") or {})}
                    for p in prompts
                ]
                batch = await rewriter.rewrite_batch_constrained(
                    prompt_dicts, parameter_columns, dialect_id, max_concurrent=5
                )
                for i, r in enumerate(batch):
                    p = prompts[i]
                    db.add(
                        Prompt(
                            project_id=project_id,
                            prompt_id=p.prompt_id,
                            prompt_text=r.get("rewritten", ""),
                            variant=dialect_id,
                            metadata_=getattr(p, "metadata_"),
                        )
                    )
                    completed += 1
                    if not r.get("success", True):
                        error_count += 1
                    job["completed_prompts"] = completed
                    job["error_count"] = error_count
                db.commit()
            else:
                rewriter = SimpleRewriter(client)
                for p in prompts:
                    r = await rewriter.rewrite(p.prompt_text, dialect_id)
                    db.add(
                        Prompt(
                            project_id=project_id,
                            prompt_id=p.prompt_id,
                            prompt_text=r.get("rewritten", ""),
                            variant=dialect_id,
                            metadata_=getattr(p, "metadata_"),
                        )
                    )
                    completed += 1
                    if not r.get("success", True):
                        error_count += 1
                    job["completed_prompts"] = completed
                    job["error_count"] = error_count
                db.commit()
        job["status"] = "completed"
        job["completed_prompts"] = completed
        job["error_count"] = error_count
    except Exception as e:
        job = _dialect_jobs.get(job_id)
        if job:
            job["status"] = "failed"
            job["message"] = str(e)
    finally:
        db.close()


@router.post("/generate", response_model=GenerateResponse)
def start_generate(
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start dialect generation for all prompts in the project. Returns immediately with job_id."""
    project = db.query(Project).filter(Project.id == body.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    total_prompts = db.query(Prompt).filter(Prompt.project_id == body.project_id).count()
    if total_prompts == 0:
        raise HTTPException(status_code=400, detail="Project has no prompts")
    for did in body.dialect_ids:
        if did not in AVAILABLE_DIALECTS:
            raise HTTPException(status_code=400, detail=f"Unknown dialect: {did}")

    job_id = str(uuid.uuid4())
    total_work = total_prompts * len(body.dialect_ids)
    _dialect_jobs[job_id] = {
        "status": "started",
        "total_prompts": total_work,
        "completed_prompts": 0,
        "error_count": 0,
        "dialects": body.dialect_ids,
        "message": None,
    }
    background_tasks.add_task(
        _run_dialect_generation,
        job_id=job_id,
        project_id=body.project_id,
        dialect_ids=body.dialect_ids,
        provider=body.provider,
        api_key=body.api_key,
        model=body.model,
        base_url=body.base_url,
        constrained=body.constrained,
        parameter_columns=body.parameter_columns,
    )
    return GenerateResponse(
        job_id=job_id,
        status="started",
        total_prompts=total_prompts,
        dialects=body.dialect_ids,
    )


@router.get("/generate/{job_id}/progress", response_model=GenerateProgressResponse)
def get_generate_progress(job_id: str):
    """Return progress of a dialect generation job."""
    job = _dialect_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    total = job.get("total_prompts", 0)
    completed = job.get("completed_prompts", 0)
    progress_pct = (completed / total * 100.0) if total else 0.0
    return GenerateProgressResponse(
        job_id=job_id,
        status=job.get("status", "unknown"),
        total_prompts=total,
        completed_prompts=completed,
        error_count=job.get("error_count", 0),
        progress_pct=round(progress_pct, 2),
        dialects=job.get("dialects", []),
        message=job.get("message"),
    )
