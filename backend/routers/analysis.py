"""
Endpoints for statistical analysis and result export.
"""

from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db import Prompt, Result, Run, get_db
from models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    CompletenessRequest,
    DirectionalBiasRequest,
    DifferenceRequest,
    ExportRequest,
)
from analysis.difference import run_difference_lpm
from analysis.directional_bias import run_directional_bias
from analysis.completeness import run_completeness_analysis
from analysis.export import results_to_latex, results_to_csv, results_to_json
from fastapi.responses import Response

router = APIRouter()


def _load_results_df(
    db: Session,
    project_id: str,
    run_ids: List[str],
) -> pd.DataFrame:
    """Load results for given project and run_ids into a DataFrame with prompt_id, variant, model_id, parsed_index, raw_response, is_valid, error_message, features_applied. Joins prompts for variant and features_applied."""
    from db import Project

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    runs = db.query(Run).filter(Run.project_id == project_id, Run.id.in_(run_ids)).all()
    if not runs:
        raise HTTPException(status_code=404, detail="No runs found for this project and run_ids")
    valid_run_ids = {r.id for r in runs}

    rows: List[Dict[str, Any]] = []
    q = (
        db.query(
            Result.run_id,
            Result.prompt_id,
            Result.raw_response,
            Result.parsed_index,
            Result.is_valid,
            Result.error_message,
            Result.latency_ms,
            Result.created_at,
            Prompt.prompt_id.label("prompt_id_str"),
            Prompt.variant,
            Prompt.features_applied,
            Run.model_id,
            Run.model_provider,
        )
        .join(Prompt, Result.prompt_id == Prompt.id)
        .join(Run, Result.run_id == Run.id)
        .filter(Result.run_id.in_(valid_run_ids), Run.project_id == project_id)
    )
    for r in q.all():
        rows.append({
            "prompt_id": r.prompt_id_str,
            "variant": r.variant,
            "model_id": r.model_id,
            "parsed_index": r.parsed_index,
            "raw_response": r.raw_response,
            "is_valid": r.is_valid,
            "error_message": r.error_message,
            "latency_ms": r.latency_ms,
            "run_id": r.run_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "features_applied": r.features_applied,
        })

    default_columns = ["prompt_id", "variant", "model_id", "parsed_index", "raw_response", "is_valid", "error_message", "features_applied"]
    if not rows:
        return pd.DataFrame(columns=default_columns)
    return pd.DataFrame(rows)


@router.post("/difference")
def post_difference(data: DifferenceRequest, db: Session = Depends(get_db)):
    """Run difference LPM analysis on specified runs. Returns difference rates per model per variant. Filters out is_valid=False before analysis."""
    df = _load_results_df(db, data.project_id, data.run_ids)
    if df.empty:
        return {"model_id": {}}
    df_valid = df[df["is_valid"].fillna(0).astype(int) == 1] if "is_valid" in df.columns else df
    try:
        results = run_difference_lpm(df_valid, baseline_variant=data.baseline_variant)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return results


@router.post("/directional-bias")
def post_directional_bias(data: DirectionalBiasRequest, db: Session = Depends(get_db)):
    """Run directional bias analysis. Returns mean difference vs baseline per model per variant. Filters out is_valid=False before analysis."""
    df = _load_results_df(db, data.project_id, data.run_ids)
    if df.empty:
        return {"model_id": {}}
    df_valid = df[df["is_valid"].fillna(0).astype(int) == 1] if "is_valid" in df.columns else df
    try:
        results = run_directional_bias(df_valid, baseline_variant=data.baseline_variant)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return results


@router.post("/completeness")
def post_completeness(data: CompletenessRequest, db: Session = Depends(get_db)):
    """Run completeness analysis (valid/invalid/refusals/empty) per model per variant. Includes all results (including is_valid=False)."""
    df = _load_results_df(db, data.project_id, data.run_ids)
    if df.empty:
        return {"model_id": {}}
    try:
        results = run_completeness_analysis(df)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return results


@router.post("/export")
def post_export(data: ExportRequest, db: Session = Depends(get_db)):
    """Export analysis as LaTeX, CSV, or JSON. For latex/csv returns downloadable file."""
    df = _load_results_df(db, data.project_id, data.run_ids)

    if data.table_type == "difference":
        df_valid = df[df["is_valid"].fillna(0).astype(int) == 1] if not df.empty and "is_valid" in df.columns else df
        analysis_results = run_difference_lpm(df_valid, baseline_variant="standard") if not df_valid.empty else {}
    elif data.table_type == "directional_bias":
        df_valid = df[df["is_valid"].fillna(0).astype(int) == 1] if not df.empty and "is_valid" in df.columns else df
        analysis_results = run_directional_bias(df_valid, baseline_variant="standard") if not df_valid.empty else {}
    elif data.table_type == "completeness":
        analysis_results = run_completeness_analysis(df) if not df.empty else {}
    else:
        raise HTTPException(status_code=400, detail=f"Unknown table_type: {data.table_type}")

    if data.format == "json":
        return results_to_json(analysis_results)

    if data.format == "latex":
        content = results_to_latex(analysis_results, data.table_type)
        return Response(
            content=content,
            media_type="application/x-latex",
            headers={"Content-Disposition": f'attachment; filename="analysis_{data.table_type}.tex"'},
        )
    if data.format == "csv":
        content = results_to_csv(analysis_results, data.table_type)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="analysis_{data.table_type}.csv"'},
        )
    raise HTTPException(status_code=400, detail="format must be latex, csv, or json")


@router.get("/results/{project_id}")
def get_results(
    project_id: str,
    db: Session = Depends(get_db),
    run_id: Optional[str] = Query(None),
    variant: Optional[str] = Query(None),
    model_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """Return raw results table with optional filters and pagination."""
    from db import Project

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    q = (
        db.query(Result, Prompt, Run)
        .join(Prompt, Result.prompt_id == Prompt.id)
        .join(Run, Result.run_id == Run.id)
        .filter(Run.project_id == project_id)
    )
    if run_id is not None:
        q = q.filter(Result.run_id == run_id)
    if variant is not None:
        q = q.filter(Prompt.variant == variant)
    if model_id is not None:
        q = q.filter(Run.model_id == model_id)

    total = q.count()
    offset = (page - 1) * per_page
    rows = q.order_by(Result.id).offset(offset).limit(per_page).all()

    items = []
    for res, prompt, run in rows:
        items.append({
            "id": res.id,
            "run_id": res.run_id,
            "prompt_id": prompt.prompt_id,
            "prompt_text": getattr(prompt, "prompt_text", None) or "",
            "prompt_db_id": res.prompt_id,
            "variant": prompt.variant,
            "model_id": run.model_id,
            "model_provider": run.model_provider,
            "raw_response": res.raw_response,
            "parsed_label": res.parsed_label,
            "parsed_index": res.parsed_index,
            "is_valid": res.is_valid,
            "error_message": res.error_message,
            "latency_ms": res.latency_ms,
            "created_at": res.created_at.isoformat() if res.created_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/", response_model=AnalysisResponse)
def run_analysis(data: AnalysisRequest, db: Session = Depends(get_db)):
    """Run statistical analysis (difference, directional_bias, or completeness) on specified runs. Requires project_id in body if using run_ids from a project."""
    raise NotImplementedError("Use POST /difference, /directional-bias, or /completeness with project_id and run_ids.")