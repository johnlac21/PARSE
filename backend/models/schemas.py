"""
Pydantic models for API request/response.

Defines: ProjectCreate, ProjectResponse, PromptUpload, VariantPreviewRequest,
VariantPreviewResponse, RunCreate, RunResponse, RunProgress, AnalysisRequest,
AnalysisResponse, ExportRequest.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

TaskModality = Literal["likert", "recommendation_list", "free_text"]


class ProjectCreate(BaseModel):
    """Request body for creating a project."""

    name: str = Field(..., min_length=1, max_length=100)
    task_modality: TaskModality
    config: Optional[Dict[str, Any]] = None

    @field_validator("name")
    @classmethod
    def name_non_empty_stripped(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("Project name must be non-empty")
        return s


class ProjectResponse(BaseModel):
    """Response model for a project."""

    id: str
    name: str
    task_modality: str
    created_at: datetime
    config: Optional[Dict[str, Any]] = None
    prompt_count: Optional[int] = None
    run_count: Optional[int] = None

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    """Response after uploading prompts file."""

    prompts_loaded: int
    columns_detected: List[str]
    sample: List[Dict[str, Any]]


class MapColumnsRequest(BaseModel):
    """Request to re-map columns for already uploaded data."""

    prompt_id_column: str
    prompt_text_column: str = Field(..., min_length=1)
    variant_column: Optional[str] = None
    metadata_columns: List[str] = Field(default_factory=list)


class DefaultDatasetUploadRequest(BaseModel):
    """Request to load a bundled default prompt CSV (see POST .../upload/default)."""

    dataset: str


class PromptResponse(BaseModel):
    """Single prompt in list/detail."""

    id: int
    prompt_id: str
    prompt_text: str
    variant: str
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class PaginatedPromptsResponse(BaseModel):
    """Paginated list of prompts."""

    items: List[PromptResponse]
    total: int
    page: int
    per_page: int


class PromptUpload(BaseModel):
    """Request body for uploading prompts to a project."""

    prompts: List[Dict[str, Any]] = Field(..., description="List of prompt records (prompt_id, text, etc.)")


class VariantPreviewRequest(BaseModel):
    """Request body for variant preview (1-10 sample texts)."""

    texts: List[str] = Field(..., min_length=1, max_length=10)
    grammar_features: List[str] = Field(default_factory=list)
    grammar_mode: Literal["individual", "all_combinations", "bundle"] = "individual"
    typo_features: List[str] = Field(default_factory=list)
    typo_word_p: float = Field(0.15, ge=0.0, le=1.0)
    typo_char_p: float = Field(0.6, ge=0.0, le=1.0)
    seed: int = 42


class VariantPreviewItem(BaseModel):
    """Single variant in preview response."""

    original_text: str
    variant_id: str
    variant_type: str
    transformed_text: str
    features_applied: List[str]
    changes_made: bool


class VariantPreviewResponse(BaseModel):
    """Response for variant preview."""

    variants: List[VariantPreviewItem]
    total_variant_count: int
    summary: Dict[str, int]  # grammar_variants, typo_variants


class CheckApplicabilityRequest(BaseModel):
    """Request for checking grammar feature applicability on project prompts."""

    project_id: str
    feature_ids: List[str] = Field(...)


class FeatureApplicabilityItem(BaseModel):
    """Per-feature applicability result."""

    feature_id: str
    name: str
    total_applicable: int
    total_prompts: int
    applicability_rate: float
    applicable: bool


class CheckApplicabilityResponse(BaseModel):
    """Response for check-applicability."""

    features: List[FeatureApplicabilityItem]
    matrix: Optional[Dict[str, Any]] = None  # per-prompt applicability when <500 prompts


class VariantGenerateRequest(BaseModel):
    """Request for generating all variants for a project."""

    project_id: str
    grammar_features: List[str] = Field(default_factory=list)
    grammar_mode: Literal["individual", "all_combinations", "bundle"] = "individual"
    typo_features: List[str] = Field(default_factory=list)
    typo_word_p: float = Field(0.15, ge=0.0, le=1.0)
    typo_char_p: float = Field(0.6, ge=0.0, le=1.0)
    seed: int = 42


class VariantGenerateResponse(BaseModel):
    """Response after generating variants."""

    variants_generated: int
    prompts_processed: int


class RunCreate(BaseModel):
    """Request body for creating/starting a run."""

    project_id: str
    model_provider: str
    model_id: str
    api_key: Optional[str] = None  # NOT persisted to DB
    system_prompt: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = None
    base_url: Optional[str] = None  # For Ollama/custom endpoints


class RunResponse(BaseModel):
    """Response model for a run."""

    id: str
    project_id: str
    model_provider: str
    model_id: str
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_prompts: int
    completed_prompts: int
    error_count: int

    class Config:
        from_attributes = True


class RunProgress(BaseModel):
    """Progress update for a run."""

    run_id: str
    status: str
    total_prompts: int
    completed_prompts: int
    error_count: int
    progress_pct: float
    eta_seconds: Optional[int] = None
    message: Optional[str] = None  # e.g. "rate limited, retrying..."


class AnalysisRequest(BaseModel):
    """Request body for statistical analysis."""

    run_ids: List[str] = Field(..., description="Run IDs to include in analysis")
    analysis_type: str = Field(..., description="e.g. difference, directional_bias, completeness")


class AnalysisResponse(BaseModel):
    """Response model for analysis results."""

    analysis_type: str
    run_ids: List[str]
    results: Dict[str, Any] = Field(default_factory=dict)


class DifferenceRequest(BaseModel):
    """Request for difference LPM analysis."""

    project_id: str
    run_ids: List[str] = Field(..., description="Run IDs to include")
    baseline_variant: str = "standard"


class DirectionalBiasRequest(BaseModel):
    """Request for directional bias analysis."""

    project_id: str
    run_ids: List[str] = Field(..., description="Run IDs to include")
    baseline_variant: str = "standard"


class CompletenessRequest(BaseModel):
    """Request for completeness analysis."""

    project_id: str
    run_ids: List[str] = Field(..., description="Run IDs to include")


class ExportRequest(BaseModel):
    """Request body for exporting analysis data."""

    project_id: str
    run_ids: List[str] = Field(..., description="Run IDs to include")
    table_type: str = Field(..., description="One of: difference, directional_bias, completeness")
    format: Literal["latex", "csv", "json"] = Field(..., description="Export format")
