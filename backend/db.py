"""
SQLite database setup with SQLAlchemy.

Defines tables: projects, prompts, runs, results.
Database file: sqlite:///./parse.db
Uses context manager for sessions with proper rollback on errors.
"""

import logging
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

Base = declarative_base()


class Project(Base):
    """Projects table: id (TEXT PK), name, task_modality, created_at, config (JSON)."""

    __tablename__ = "projects"
    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    task_modality = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    config = Column(JSON, nullable=True)


class Prompt(Base):
    """Prompts table: id (INTEGER PK), project_id FK, prompt_id, prompt_text, variant, features_applied JSON, metadata JSON."""

    __tablename__ = "prompts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Text, ForeignKey("projects.id"), nullable=False)
    prompt_id = Column(Text, nullable=False)
    prompt_text = Column(Text, nullable=False)
    variant = Column(Text, nullable=False)
    features_applied = Column(JSON, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)


class Run(Base):
    """Runs table: id (TEXT PK), project_id FK, model_provider, model_id, system_prompt, temperature, status, started_at, completed_at, total_prompts, completed_prompts, error_count, progress_message."""

    __tablename__ = "runs"
    id = Column(Text, primary_key=True)
    project_id = Column(Text, ForeignKey("projects.id"), nullable=False)
    model_provider = Column(Text, nullable=False)
    model_id = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=True)
    temperature = Column(Float, nullable=True)
    status = Column(Text, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_prompts = Column(Integer, nullable=False)
    completed_prompts = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    progress_message = Column(Text, nullable=True)  # e.g. "rate limited, retrying..."


class UploadStaging(Base):
    """Staging table for upload re-mapping: project_id, row_index, data (JSON)."""

    __tablename__ = "upload_staging"
    project_id = Column(Text, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    row_index = Column(Integer, primary_key=True)
    data = Column(JSON, nullable=False)


class Result(Base):
    """Results table: id (INTEGER PK), run_id FK, prompt_id FK, raw_response, parsed_label, parsed_index, is_valid, error_message, latency_ms, created_at."""

    __tablename__ = "results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Text, ForeignKey("runs.id"), nullable=False)
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False)
    raw_response = Column(Text, nullable=True)
    parsed_label = Column(Text, nullable=True)
    parsed_index = Column(Integer, nullable=True)
    is_valid = Column(Integer, nullable=True)  # SQLite uses 0/1 for boolean
    error_message = Column(Text, nullable=True)
    latency_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


DATABASE_URL = "sqlite:///./parse.db"
# StaticPool: single connection per process for SQLite (avoids threading issues, connection reuse).
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def session_scope():
    """Context manager for database sessions. Rolls back on exception, commits on success."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Database session rollback due to error")
        raise
    finally:
        session.close()


def get_db():
    """Yield a database session; close after use. For FastAPI Depends()."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        logger.exception("Database session rollback due to error")
        raise
    finally:
        db.close()
