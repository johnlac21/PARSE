"""
PARSE Framework API - FastAPI application entry point.

Provides CORS middleware, routers, startup event, health check,
custom exception handlers, and request timing logging.
"""

import logging
import time
import traceback

from sqlalchemy import text

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from db import Base, engine
from routers import analysis, dialect, projects, runs, variants
from utils.errors import (
    FeatureNotFound,
    LLMError,
    ParseError,
    ProjectNotFound,
    RunNotFound,
)
from utils.startup import ensure_transforms_loaded, get_feature_counts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="PARSE Framework API")


@app.on_event("startup")
def on_startup() -> None:
    """Initialize database and load grammar/typo transforms."""
    Base.metadata.create_all(bind=engine)
    # Add progress_message to runs if missing (e.g. existing SQLite DBs)
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM pragma_table_info('runs') WHERE name='progress_message'"))
            row = result.fetchone()
            if row and row[0] == 0:
                conn.execute(text("ALTER TABLE runs ADD COLUMN progress_message TEXT"))
                conn.commit()
                logger.info("Added progress_message column to runs table")
    except Exception as e:
        logger.warning("Could not add progress_message column (may already exist): %s", e)
    ensure_transforms_loaded()
    n_grammar, m_typo = get_feature_counts()
    msg = f"PARSE Framework API started. {n_grammar} grammar features, {m_typo} typo features registered."
    logger.info(msg)
    print(msg)

# CORS: if you still get "Could not reach the server", try allow_origins=["*"] and allow_credentials=False
_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://[::1]:3000",
    "http://[::1]:3001",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(variants.router, prefix="/api/variants", tags=["variants"])
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(dialect.router, prefix="/api/dialect", tags=["dialect"])


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every API request with method, path, and duration."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s %s %.2fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.exception_handler(ProjectNotFound)
async def project_not_found_handler(request: Request, exc: ProjectNotFound) -> JSONResponse:
    logger.warning("Project not found: %s", exc.project_id)
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(FeatureNotFound)
async def feature_not_found_handler(request: Request, exc: FeatureNotFound) -> JSONResponse:
    logger.warning("Feature not found: %s", exc.feature_id)
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(RunNotFound)
async def run_not_found_handler(request: Request, exc: RunNotFound) -> JSONResponse:
    logger.warning("Run not found: %s", exc.run_id)
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ParseError)
async def parse_error_handler(request: Request, exc: ParseError) -> JSONResponse:
    logger.warning("Parse error: %s", exc)
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    code = exc.status_code if getattr(exc, "status_code", None) == 429 else 502
    logger.warning("LLM error: %s", exc)
    return JSONResponse(status_code=code, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled exceptions, log with traceback, return 500 with detail."""
    logger.exception(
        "Unhandled exception: %s\n%s",
        exc,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


@app.get("/api/health")
def health_check():
    """Health check endpoint for liveness/readiness probes."""
    return {"status": "ok"}
