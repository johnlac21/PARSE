"""
Endpoints for variant generation, preview, and applicability checking.

Triggers grammar and typo transform registration on module import.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlalchemy.orm import Session

from db import get_db, Prompt, Result, Run
from engine.combinator import (
    generate_all_variants,
    generate_grammar_variants,
    generate_typo_variants,
)
from engine.grammar import batch_check_applicability
from engine.grammar.registry import GRAMMAR_REGISTRY
from engine.typos.registry import TYPO_REGISTRY
from utils.errors import FeatureNotFound

# Trigger registration of grammar transforms (adds transform/applicability to GRAMMAR_REGISTRY)
import engine.grammar.transforms  # noqa: F401
# Typo registry is populated on import of registry
import engine.typos.registry  # noqa: F401

from models.schemas import (
    CheckApplicabilityRequest,
    CheckApplicabilityResponse,
    FeatureApplicabilityItem,
    VariantGenerateRequest,
    VariantGenerateResponse,
    VariantPreviewRequest,
    VariantPreviewResponse,
    VariantPreviewItem,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Maximum number of prompts for which we return per-prompt matrix in check-applicability
_CHECK_APPLICABILITY_MATRIX_MAX_PROMPTS = 500


def _get_base_prompts_for_project(db: Session, project_id: str) -> list[tuple[str, str, dict | None]]:
    """Return list of (prompt_id, prompt_text, metadata) for "standard" prompts. If none, use first row per prompt_id."""
    rows = db.query(Prompt).filter(Prompt.project_id == project_id).all()
    if not rows:
        return []
    # Prefer variant == "standard"
    by_id: dict[str, tuple[str, str, dict | None]] = {}
    for p in rows:
        meta = getattr(p, "metadata_", None) or None
        if p.variant == "standard":
            by_id[p.prompt_id] = (p.prompt_id, p.prompt_text, meta)
    for p in rows:
        if p.prompt_id not in by_id:
            meta = getattr(p, "metadata_", None) or None
            by_id[p.prompt_id] = (p.prompt_id, p.prompt_text, meta)
    return list(by_id.values())


def _prompt_list_for_applicability(db: Session, project_id: str) -> tuple[list[str], list[str]]:
    """Return (prompt_ids, texts) for unique prompts (one per prompt_id) for applicability check."""
    base = _get_base_prompts_for_project(db, project_id)
    prompt_ids = [b[0] for b in base]
    texts = [b[1] for b in base]
    return prompt_ids, texts


def _validate_feature_ids_any_registry(feature_ids: list[str]) -> None:
    """Validate that each feature_id exists in either GRAMMAR_REGISTRY or TYPO_REGISTRY. Raises FeatureNotFound."""
    for fid in feature_ids:
        if fid in GRAMMAR_REGISTRY or fid in TYPO_REGISTRY:
            continue
        raise FeatureNotFound(fid, "grammar/typo registry")


def _validate_grammar_feature_ids(feature_ids: list[str]) -> None:
    """Validate that all feature_ids exist in GRAMMAR_REGISTRY. Raises FeatureNotFound."""
    for fid in feature_ids:
        if fid not in GRAMMAR_REGISTRY:
            raise FeatureNotFound(fid, "grammar")


def _validate_typo_feature_ids(feature_ids: list[str]) -> None:
    """Validate that all feature_ids exist in TYPO_REGISTRY. Raises FeatureNotFound."""
    for fid in feature_ids:
        if fid not in TYPO_REGISTRY:
            raise FeatureNotFound(fid, "typo")


@router.post("/preview", response_model=VariantPreviewResponse)
def variant_preview(data: VariantPreviewRequest):
    """Generate a preview of variants for 1-10 sample texts with given grammar/typo features."""
    grammar_features = data.grammar_features or []
    typo_features = data.typo_features or []
    grammar_mode = data.grammar_mode
    typo_word_p = data.typo_word_p
    typo_char_p = data.typo_char_p
    seed = data.seed

    variants_out: list[VariantPreviewItem] = []
    n_grammar_per_text = 0
    n_typo_per_text = 0

    for text in data.texts:
        if not text.strip():
            continue
        grammar_variants = generate_grammar_variants(text, grammar_features, mode=grammar_mode)
        typo_variants = generate_typo_variants(
            text, typo_features, word_p=typo_word_p, char_p=typo_char_p, seed=seed
        )
        if not n_grammar_per_text and not n_typo_per_text:
            n_grammar_per_text = len(grammar_variants)
            n_typo_per_text = len(typo_variants)

        for v in grammar_variants:
            variants_out.append(
                VariantPreviewItem(
                    original_text=v["original_text"],
                    variant_id=v["variant_id"],
                    variant_type=v["variant_type"],
                    transformed_text=v["text"],
                    features_applied=v.get("features_applied", []),
                    changes_made=v.get("changes_made", False),
                )
            )
        for v in typo_variants:
            variants_out.append(
                VariantPreviewItem(
                    original_text=v["original_text"],
                    variant_id=v["variant_id"],
                    variant_type=v["variant_type"],
                    transformed_text=v["text"],
                    features_applied=[v.get("typo_type", v["variant_id"])],
                    changes_made=v["text"] != v["original_text"],
                )
            )

    total_variant_count = len(variants_out)
    summary = {
        "grammar_variants": n_grammar_per_text,
        "typo_variants": n_typo_per_text,
    }
    return VariantPreviewResponse(
        variants=variants_out,
        total_variant_count=total_variant_count,
        summary=summary,
    )


@router.post("/check-applicability", response_model=CheckApplicabilityResponse)
def check_applicability(
    data: CheckApplicabilityRequest,
    db: Session = Depends(get_db),
):
    """Load all prompts for the project and run batch applicability for the given grammar features."""
    project_id = data.project_id
    feature_ids = data.feature_ids or []

    # Resolve project and get prompts
    from db import Project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    prompt_ids, texts = _prompt_list_for_applicability(db, project_id)
    if not texts:
        return CheckApplicabilityResponse(
            features=[],
            matrix=None,
        )

    if not feature_ids:
        return CheckApplicabilityResponse(
            features=[],
            matrix=None,
        )

    _validate_feature_ids_any_registry(feature_ids)

    try:
        batch = batch_check_applicability(texts, feature_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    summary = batch["summary"]
    matrix_raw = batch["matrix"]
    n_prompts = len(texts)

    features_out: list[FeatureApplicabilityItem] = []
    for fid in feature_ids:
        s = summary[fid]
        rate = s["applicability_rate"]
        name = GRAMMAR_REGISTRY[fid].name if fid in GRAMMAR_REGISTRY else fid
        features_out.append(
            FeatureApplicabilityItem(
                feature_id=fid,
                name=name,
                total_applicable=s["total_applicable"],
                total_prompts=s["total_prompts"],
                applicability_rate=rate,
                applicable=rate > 0,
            )
        )

    matrix_response: dict[str, Any] | None = None
    if n_prompts < _CHECK_APPLICABILITY_MATRIX_MAX_PROMPTS:
        # Per-prompt: map prompt_id -> { feature_id: match_count }
        matrix_response = {}
        for i, pid in enumerate(prompt_ids):
            matrix_response[pid] = {fid: matrix_raw[fid][i] for fid in feature_ids}

    return CheckApplicabilityResponse(
        features=features_out,
        matrix=matrix_response,
    )


@router.get("/grammar-features")
def list_grammar_features():
    """Return all registered grammar features with metadata."""
    out = []
    for f in GRAMMAR_REGISTRY.values():
        out.append({
            "id": f.id,
            "name": f.name,
            "description": f.description,
            "example_std": f.example_std,
            "example_var": f.example_var,
            "category": f.category,
            "dialects": f.dialects,
            "requires_pos_tags": f.requires_pos_tags,
            "tier": f.tier,
        })
    return out


@router.get("/typo-features")
def list_typo_features():
    """Return all registered typo features with metadata."""
    out = []
    for f in TYPO_REGISTRY.values():
        out.append({
            "id": f.id,
            "name": f.name,
            "description": f.description,
            "example": f.example,
            "default_word_p": f.default_word_p,
            "default_char_p": f.default_char_p,
        })
    return out


@router.post("/generate", response_model=VariantGenerateResponse)
def generate_variants(
    data: VariantGenerateRequest,
    db: Session = Depends(get_db),
):
    """Generate all variants for all prompts in the project and store them in the prompts table."""
    project_id = data.project_id
    grammar_features = data.grammar_features or []
    typo_features = data.typo_features or []
    grammar_mode = data.grammar_mode
    typo_word_p = data.typo_word_p
    typo_char_p = data.typo_char_p
    seed = data.seed

    from db import Project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    base_prompts = _get_base_prompts_for_project(db, project_id)
    if not base_prompts:
        raise HTTPException(status_code=400, detail="Project has no prompts. Upload prompts first.")

    if grammar_features:
        _validate_grammar_feature_ids(grammar_features)
    if typo_features:
        _validate_typo_feature_ids(typo_features)

    # Generate variants for each base prompt (use row id for prompt_id in generate_all_variants? No - we use logical prompt_id)
    # We need a stable prompt row id for generate_all_variants - it's used only for attaching prompt_id to variant dicts.
    # We'll create new rows so we don't need existing Prompt.id.
    all_rows_to_insert: list[dict] = []
    variants_generated = 0

    for prompt_id, prompt_text, metadata in base_prompts:
        variant_list = generate_all_variants(
            text=prompt_text,
            prompt_id=0,  # not used for storage
            grammar_features=grammar_features,
            grammar_mode=grammar_mode,
            typo_features=typo_features,
            typo_word_p=typo_word_p,
            typo_char_p=typo_char_p,
            seed=seed,
            include_cross_combinations=False,
        )
        for v in variant_list:
            variant_id = v.get("variant_id", "standard")
            text = v.get("text", prompt_text)
            features_applied = v.get("features_applied")
            if variant_id != "standard":
                variants_generated += 1
            all_rows_to_insert.append({
                "project_id": project_id,
                "prompt_id": prompt_id,
                "prompt_text": text,
                "variant": variant_id,
                "features_applied": features_applied,
                "metadata_": metadata,
            })

    # Replace all prompts for this project (remove results that reference prompts first to avoid FK violation)
    run_ids = [r.id for r in db.query(Run.id).filter(Run.project_id == project_id).all()]
    if run_ids:
        db.execute(delete(Result).where(Result.run_id.in_(run_ids)))
    db.execute(delete(Prompt).where(Prompt.project_id == project_id))
    for row in all_rows_to_insert:
        db.add(
            Prompt(
                project_id=row["project_id"],
                prompt_id=row["prompt_id"],
                prompt_text=row["prompt_text"],
                variant=row["variant"],
                features_applied=row["features_applied"],
                metadata_=row["metadata_"],
            )
        )
    db.commit()

    return VariantGenerateResponse(
        variants_generated=variants_generated,
        prompts_processed=len(base_prompts),
    )
