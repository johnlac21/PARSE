"""
CRUD endpoints for projects.
"""

import io
import json
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import delete, func
from sqlalchemy.orm import Session

from db import Project, Prompt, Result, Run, UploadStaging, get_db
from models.schemas import (
    DefaultDatasetUploadRequest,
    MapColumnsRequest,
    PaginatedPromptsResponse,
    ProjectCreate,
    ProjectResponse,
    PromptResponse,
    UploadResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# File upload limits
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_UPLOAD_EXTENSIONS = (".csv", ".jsonl")

# Column names to try for auto-detect (in order of preference)
PROMPT_TEXT_CANDIDATES = ["prompt_text", "text", "prompt"]
PROMPT_ID_CANDIDATES = ["prompt_id", "id"]
VARIANT_CANDIDATES = ["variant", "dialect"]
KNOWN_COLUMNS = ["prompt_id", "prompt_text", "text", "prompt", "variant", "dialect"]


def _detect_columns(columns: list) -> tuple[str | None, str | None, str | None]:
    """Return (prompt_id_col, prompt_text_col, variant_col)."""
    cols_lower = [c.strip() for c in columns]
    prompt_id_col = None
    for c in PROMPT_ID_CANDIDATES:
        if c in cols_lower:
            prompt_id_col = c
            break
    prompt_text_col = None
    for c in PROMPT_TEXT_CANDIDATES:
        if c in cols_lower:
            prompt_text_col = c
            break
    variant_col = None
    for c in VARIANT_CANDIDATES:
        if c in cols_lower:
            variant_col = c
            break
    return prompt_id_col, prompt_text_col, variant_col


def _safe_str(v: Any) -> str:
    """Convert value to str; handle pandas/numpy and None."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if hasattr(v, "item"):
        return str(v.item())
    return str(v).strip()


def _row_to_prompt_data(row: dict, prompt_id_col: str | None, prompt_text_col: str, variant_col: str | None, metadata_columns: list) -> dict:
    """Build prompt_id, prompt_text, variant, metadata from a row dict."""
    prompt_id = _safe_str(row.get(prompt_id_col, "")) if prompt_id_col else ""
    prompt_text = _safe_str(row.get(prompt_text_col, ""))
    variant = _safe_str(row.get(variant_col, "standard")) if variant_col else "standard"
    if not variant:
        variant = "standard"
    metadata = {}
    for k in metadata_columns:
        if k in row:
            v = row[k]
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                metadata[k] = v.item() if hasattr(v, "item") else v
    return {"prompt_id": prompt_id, "prompt_text": prompt_text, "variant": variant, "metadata": metadata}


def _validate_upload_file(content: bytes, filename: str) -> None:
    """Validate file size and extension. Raises HTTPException if invalid."""
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_BYTES // (1024*1024)} MB.",
        )
    name_lower = (filename or "").lower()
    if not any(name_lower.endswith(ext) for ext in ALLOWED_UPLOAD_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="File must be CSV or JSONL (.csv or .jsonl)",
        )


def _rows_from_upload(content: bytes, filename: str) -> tuple[list[dict], list[str]]:
    """Parse CSV or JSONL file; return (list of row dicts, list of column names)."""
    name_lower = (filename or "").lower()
    if name_lower.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content))
        columns = list(df.columns)
        rows = df.to_dict(orient="records")
        # Convert any non-serializable values for JSON storage
        for r in rows:
            for k, v in list(r.items()):
                if pd.isna(v):
                    r[k] = None
                elif hasattr(v, "item"):
                    r[k] = v.item()
        return rows, columns
    if name_lower.endswith(".jsonl"):
        lines = content.decode("utf-8", errors="replace").strip().splitlines()
        rows = []
        columns_set = set()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
                columns_set.update(obj.keys())
        columns = list(columns_set)
        return rows, columns
    raise HTTPException(status_code=400, detail="File must be CSV or JSONL (.csv or .jsonl)")


@router.post("/", response_model=ProjectResponse, status_code=201)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project."""
    project_id = str(uuid4())
    project = Project(
        id=project_id,
        name=data.name,
        task_modality=data.task_modality,
        config=data.config,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        task_modality=project.task_modality,
        created_at=project.created_at,
        config=project.config,
    )


@router.get("/", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    """List all projects with prompt_count."""
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    prompt_counts = (
        db.query(Prompt.project_id, func.count(Prompt.id).label("cnt"))
        .group_by(Prompt.project_id)
        .all()
    )
    count_by_project = {pid: cnt for pid, cnt in prompt_counts}
    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            task_modality=p.task_modality,
            created_at=p.created_at,
            config=p.config,
            prompt_count=count_by_project.get(p.id, 0),
        )
        for p in projects
    ]


def _get_project_or_404(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# Bundled default CSVs live under <backend package>/prompts/ (parent of routers/ is backend root)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DATASET_FILES: dict[str, str] = {
    "privacy_bias": "Privacy_Bias.csv",
}


def _ingest_rows(db: Session, project_id: str, rows: list[dict], columns: list) -> UploadResponse:
    """
    Store rows in upload staging, auto-detect columns, and build Prompt rows when text column is found.
    Used by file upload and bundled default CSV endpoints.
    """
    # Clear existing staging and prompts (and dependent runs/results) for this project
    run_ids = [r.id for r in db.query(Run.id).filter(Run.project_id == project_id).all()]
    if run_ids:
        db.execute(delete(Result).where(Result.run_id.in_(run_ids)))
    db.execute(delete(Run).where(Run.project_id == project_id))
    db.execute(delete(Prompt).where(Prompt.project_id == project_id))
    db.execute(delete(UploadStaging).where(UploadStaging.project_id == project_id))
    for i, row in enumerate(rows):
        db.add(UploadStaging(project_id=project_id, row_index=i, data=dict(row)))
    db.commit()

    prompt_id_col, prompt_text_col, variant_col = _detect_columns(columns)
    metadata_columns = [c for c in columns if c not in KNOWN_COLUMNS]

    if not prompt_text_col:
        return UploadResponse(
            prompts_loaded=0,
            columns_detected=list(columns),
            sample=rows[:5],
        )

    # Build prompts from staging (reload from DB to keep one source of truth)
    db.execute(delete(Prompt).where(Prompt.project_id == project_id))
    staging_rows = (
        db.query(UploadStaging)
        .filter(UploadStaging.project_id == project_id)
        .order_by(UploadStaging.row_index)
        .all()
    )
    loaded = 0
    for i, sr in enumerate(staging_rows):
        row = sr.data
        prompt_data = _row_to_prompt_data(row, prompt_id_col, prompt_text_col, variant_col, metadata_columns)
        if not prompt_data["prompt_text"]:
            continue
        if not prompt_data["prompt_id"]:
            prompt_data["prompt_id"] = str(i + 1)
        db.add(
            Prompt(
                project_id=project_id,
                prompt_id=prompt_data["prompt_id"],
                prompt_text=prompt_data["prompt_text"],
                variant=prompt_data["variant"],
                metadata_=prompt_data["metadata"] or None,
            )
        )
        loaded += 1

    db.commit()
    return UploadResponse(
        prompts_loaded=loaded,
        columns_detected=list(columns),
        sample=rows[:5],
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    """Get a project by ID with prompt_count and run_count."""
    project = _get_project_or_404(db, project_id)
    prompt_count = db.query(func.count(Prompt.id)).filter(Prompt.project_id == project_id).scalar() or 0
    run_count = db.query(func.count(Run.id)).filter(Run.project_id == project_id).scalar() or 0
    return ProjectResponse(
        id=project.id,
        name=project.name,
        task_modality=project.task_modality,
        created_at=project.created_at,
        config=project.config,
        prompt_count=prompt_count,
        run_count=run_count,
    )


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Delete a project and cascade: results -> runs -> prompts -> project."""
    project = _get_project_or_404(db, project_id)
    run_ids = [r.id for r in db.query(Run.id).filter(Run.project_id == project_id).all()]
    if run_ids:
        db.execute(delete(Result).where(Result.run_id.in_(run_ids)))
    db.execute(delete(Run).where(Run.project_id == project_id))
    db.execute(delete(Prompt).where(Prompt.project_id == project_id))
    db.execute(delete(UploadStaging).where(UploadStaging.project_id == project_id))
    db.delete(project)
    db.commit()
    return None


@router.post("/{project_id}/upload", response_model=UploadResponse)
async def upload_prompts(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload CSV or JSONL (max 10 MB); store staging; auto-detect columns and create prompts or return columns for mapping."""
    _get_project_or_404(db, project_id)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    _validate_upload_file(content, file.filename or "")
    rows, columns = _rows_from_upload(content, file.filename or "")
    if not rows:
        raise HTTPException(status_code=400, detail="No rows found in file")
    return _ingest_rows(db, project_id, rows, columns)


@router.post("/{project_id}/upload/default", response_model=UploadResponse)
def upload_default_dataset(
    project_id: str,
    body: DefaultDatasetUploadRequest,
    db: Session = Depends(get_db),
):
    """Load a bundled default CSV from backend/prompts/. Same ingest path as /upload."""
    _get_project_or_404(db, project_id)
    if body.dataset not in _DEFAULT_DATASET_FILES:
        raise HTTPException(
            status_code=400,
            detail="Unknown dataset. Use 'privacy_bias'.",
        )
    filename = _DEFAULT_DATASET_FILES[body.dataset]
    path = _BACKEND_ROOT / "prompts" / filename
    if not path.is_file():
        raise HTTPException(
            status_code=500,
            detail=f"Bundled default dataset file is missing: prompts/{filename}",
        )
    content = path.read_bytes()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    rows, columns = _rows_from_upload(content, filename)
    if not rows:
        raise HTTPException(status_code=400, detail="No rows found in file")
    return _ingest_rows(db, project_id, rows, columns)


@router.post("/{project_id}/upload/map-columns", response_model=UploadResponse)
def map_columns_upload(
    project_id: str,
    body: MapColumnsRequest,
    db: Session = Depends(get_db),
):
    """Re-map already uploaded staging data with user-specified column names."""
    _get_project_or_404(db, project_id)
    staging_rows = (
        db.query(UploadStaging)
        .filter(UploadStaging.project_id == project_id)
        .order_by(UploadStaging.row_index)
        .all()
    )
    if not staging_rows:
        raise HTTPException(
            status_code=400,
            detail="No uploaded data to re-map. Upload a file first.",
        )

    # Delete dependent data then prompts
    run_ids = [r.id for r in db.query(Run.id).filter(Run.project_id == project_id).all()]
    if run_ids:
        db.execute(delete(Result).where(Result.run_id.in_(run_ids)))
    db.execute(delete(Run).where(Run.project_id == project_id))
    db.execute(delete(Prompt).where(Prompt.project_id == project_id))

    metadata_columns = body.metadata_columns or []
    loaded = 0
    sample = []
    for i, sr in enumerate(staging_rows):
        row = sr.data
        prompt_data = _row_to_prompt_data(
            row,
            body.prompt_id_column,
            body.prompt_text_column,
            body.variant_column,
            metadata_columns,
        )
        if not prompt_data["prompt_text"]:
            continue
        if not prompt_data["prompt_id"]:
            prompt_data["prompt_id"] = str(i + 1)
        if not prompt_data["variant"]:
            prompt_data["variant"] = "standard"
        db.add(
            Prompt(
                project_id=project_id,
                prompt_id=prompt_data["prompt_id"],
                prompt_text=prompt_data["prompt_text"],
                variant=prompt_data["variant"],
                metadata_=prompt_data["metadata"] or None,
            )
        )
        loaded += 1
        if len(sample) < 5:
            sample.append(row)

    db.commit()
    columns_used = [body.prompt_id_column, body.prompt_text_column]
    if body.variant_column:
        columns_used.append(body.variant_column)
    columns_used.extend(metadata_columns)
    return UploadResponse(prompts_loaded=loaded, columns_detected=columns_used, sample=sample)


@router.get("/{project_id}/prompts", response_model=PaginatedPromptsResponse)
def list_prompts(
    project_id: str,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    variant_filter: str | None = Query(None, alias="variant_filter"),
):
    """Return paginated prompts for the project."""
    _get_project_or_404(db, project_id)
    q = db.query(Prompt).filter(Prompt.project_id == project_id)
    if variant_filter is not None:
        q = q.filter(Prompt.variant == variant_filter)
    total = q.count()
    offset = (page - 1) * per_page
    prompts = q.order_by(Prompt.id).offset(offset).limit(per_page).all()
    items = [
        PromptResponse(
            id=p.id,
            prompt_id=p.prompt_id,
            prompt_text=p.prompt_text,
            variant=p.variant,
            metadata=getattr(p, "metadata_", None),
        )
        for p in prompts
    ]
    return PaginatedPromptsResponse(items=items, total=total, page=page, per_page=per_page)
