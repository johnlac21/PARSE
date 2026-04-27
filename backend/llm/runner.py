"""
Async query runner for LLM requests across all variants in a run.
Handles rate limiting (429) with exponential backoff and progress updates.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from db import Result, Run
from llm.parsers import get_parser
from llm.providers import UnifiedLLMClient

logger = logging.getLogger(__name__)

RATE_LIMIT_MAX_RETRIES = 5
RATE_LIMIT_INITIAL_DELAY = 2.0
RATE_LIMIT_BACKOFF_FACTOR = 2.0


def _is_rate_limit_error(out: dict) -> bool:
    """True if the LLM response indicates a 429 rate limit."""
    if out.get("error"):
        err = (out.get("error") or "").lower()
        if "429" in err or "rate limit" in err or "rate_limit" in err:
            return True
    if out.get("status_code") == 429:
        return True
    return False


def _is_auth_error(error_message: str) -> bool:
    """True if the error looks like an authentication/API key problem (fail fast)."""
    if not error_message:
        return False
    err = error_message.lower()
    auth_phrases = (
        "api key",
        "api_key",
        "authentication",
        "authorization",
        "invalid api",
        "incorrect api",
        "invalid_api",
        "unauthorized",
        "401",
    )
    return any(p in err for p in auth_phrases)


class QueryRunner:
    """Runs LLM queries for all variants in a run, with progress tracking."""

    def __init__(self, client: UnifiedLLMClient, db: Session, run_id: str, task_modality: str = "likert"):
        self.client = client
        self.db = db
        self.run_id = run_id
        self.task_modality = task_modality
        self._cancelled = False

    async def execute_run(
        self,
        prompts: list[dict],
        system_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 150,
    ) -> None:
        """
        Queries the LLM for each prompt. Parses response with project's OutputParser,
        stores raw_response and parsed fields (parsed_label, parsed_index, is_valid) in DB.
        Skips prompts that already have results (for resume capability).
        Updates run progress in DB after each batch.
        """
        parser = get_parser(self.task_modality)
        # Skip prompts that already have a result for this run
        existing = {
            r.prompt_id
            for r in self.db.query(Result.prompt_id).filter(Result.run_id == self.run_id).distinct().all()
        }
        pending = [p for p in prompts if p["id"] not in existing]
        if not pending:
            self._mark_run_complete()
            return

        semaphore = asyncio.Semaphore(5)
        batch_size = 10

        async def run_one(prompt: dict) -> dict[str, Any]:
            async with semaphore:
                last_out = None
                for attempt in range(RATE_LIMIT_MAX_RETRIES + 1):
                    out = await self.client.query(
                        prompt=prompt["prompt_text"],
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    last_out = out
                    if not _is_rate_limit_error(out) or attempt == RATE_LIMIT_MAX_RETRIES:
                        break
                    delay = RATE_LIMIT_INITIAL_DELAY * (RATE_LIMIT_BACKOFF_FACTOR ** attempt)
                    logger.warning(
                        "LLM rate limit (429) for run_id=%s, attempt %s/%s, retrying in %.1fs",
                        self.run_id,
                        attempt + 1,
                        RATE_LIMIT_MAX_RETRIES,
                        delay,
                    )
                    self._set_progress_message("rate limited, retrying...")
                    await asyncio.sleep(delay)
                return {"prompt_id": prompt["id"], **last_out}

        for i in range(0, len(pending), batch_size):
            if self._cancelled:
                run = self.db.query(Run).filter(Run.id == self.run_id).first()
                if run and run.status == "running":
                    run.status = "cancelled"
                    run.completed_at = datetime.utcnow()
                    self.db.commit()
                return

            batch = pending[i : i + batch_size]
            results = await asyncio.gather(*[run_one(p) for p in batch], return_exceptions=True)

            batch_has_success = False
            first_error_message: str | None = None

            for j, r in enumerate(results):
                prompt_id = batch[j]["id"]
                if isinstance(r, Exception):
                    err_msg = str(r)
                    if first_error_message is None:
                        first_error_message = err_msg
                    self._store_error(prompt_id, err_msg)
                    self._increment_error_count()
                else:
                    if r.get("error"):
                        err_msg = r["error"]
                        if first_error_message is None:
                            first_error_message = err_msg
                        self._store_error(prompt_id, err_msg)
                        self._increment_error_count()
                    else:
                        batch_has_success = True
                        raw_response = r.get("raw_response") or ""
                        parsed = self._parse_response(parser, raw_response)
                        self.db.add(
                            Result(
                                run_id=self.run_id,
                                prompt_id=prompt_id,
                                raw_response=raw_response,
                                parsed_label=parsed.get("parsed_label"),
                                parsed_index=parsed.get("parsed_index"),
                                is_valid=1 if parsed.get("is_valid") else 0,
                                error_message=None,
                                latency_ms=r.get("latency_ms"),
                            )
                        )
                self._increment_completed_prompts()

            self.db.commit()
            run = self.db.query(Run).filter(Run.id == self.run_id).first()
            if run:
                logger.info(
                    "Run batch done: run_id=%s completed_prompts=%s/%s errors=%s",
                    self.run_id,
                    run.completed_prompts,
                    run.total_prompts or 0,
                    run.error_count or 0,
                )

            # Fail fast: if first batch had only errors and any looks like auth, stop and show error
            if i == 0 and not batch_has_success and first_error_message and _is_auth_error(first_error_message):
                self._mark_run_failed(first_error_message)
                return

        self._mark_run_complete()

    def _parse_response(self, parser: Any, raw_response: str) -> dict[str, Any]:
        """Parse raw_response with the project's parser. Return parsed_label, parsed_index, is_valid."""
        try:
            out = parser.parse(raw_response)
        except Exception:
            return {"parsed_label": None, "parsed_index": None, "is_valid": False}
        # LikertParser returns parsed_label, parsed_index, is_valid
        parsed_label = out.get("parsed_label")
        parsed_index = out.get("parsed_index")
        if parsed_index is not None and not isinstance(parsed_index, int):
            try:
                parsed_index = int(parsed_index)
            except (TypeError, ValueError):
                parsed_index = None
        is_valid = out.get("is_valid", False)
        return {"parsed_label": parsed_label, "parsed_index": parsed_index, "is_valid": bool(is_valid)}

    def _set_progress_message(self, message: str | None) -> None:
        run = self.db.query(Run).filter(Run.id == self.run_id).first()
        if run and hasattr(run, "progress_message"):
            run.progress_message = message
            self.db.commit()

    def _increment_completed_prompts(self) -> None:
        run = self.db.query(Run).filter(Run.id == self.run_id).first()
        if run:
            run.completed_prompts = (run.completed_prompts or 0) + 1
            if hasattr(run, "progress_message"):
                run.progress_message = None

    def _increment_error_count(self) -> None:
        run = self.db.query(Run).filter(Run.id == self.run_id).first()
        if run:
            run.error_count = (run.error_count or 0) + 1

    def _store_error(self, prompt_id: int, error_message: str) -> None:
        self.db.add(
            Result(
                run_id=self.run_id,
                prompt_id=prompt_id,
                raw_response=None,
                error_message=error_message,
                latency_ms=None,
            )
        )

    def _mark_run_complete(self) -> None:
        run = self.db.query(Run).filter(Run.id == self.run_id).first()
        if run and run.status == "running":
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            if hasattr(run, "progress_message"):
                run.progress_message = None
            self.db.commit()

    def _mark_run_failed(self, message: str) -> None:
        """Set run to failed with message so user sees error immediately."""
        run = self.db.query(Run).filter(Run.id == self.run_id).first()
        if run and run.status == "running":
            run.status = "failed"
            run.completed_at = datetime.utcnow()
            if hasattr(run, "progress_message"):
                run.progress_message = (message[:2000] if len(message) > 2000 else message)
            self.db.commit()

    def cancel(self) -> None:
        self._cancelled = True
