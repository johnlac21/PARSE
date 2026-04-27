"""
Constrained dialect rewriter using an LLM.
Single-pass (SimpleRewriter) and two-pass constrained (ConstrainedRewriter).
"""

import asyncio
from typing import Any

from engine.dialect.config import AVAILABLE_DIALECTS


class SimpleRewriter:
    """For unstructured prompts — single-pass LLM rewriting."""

    def __init__(self, llm_client: Any):
        self.client = llm_client

    async def rewrite(self, text: str, dialect_id: str) -> dict:
        """
        Single-pass rewrite.
        Returns: {"original": str, "rewritten": str, "dialect": str, "success": bool, "error": str | None}
        """
        config = AVAILABLE_DIALECTS[dialect_id]
        response = await self.client.query(
            prompt=text,
            system_prompt=config["system_prompt"],
            temperature=0.3,
        )
        return {
            "original": text,
            "rewritten": response.get("raw_response") or "",
            "dialect": dialect_id,
            "success": response.get("error") is None,
            "error": response.get("error"),
        }

    async def rewrite_batch(
        self, texts: list[str], dialect_id: str, max_concurrent: int = 5
    ) -> list[dict]:
        """Rewrite multiple texts with concurrency control."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def one(text: str) -> dict:
            async with semaphore:
                return await self.rewrite(text, dialect_id)

        return await asyncio.gather(*[one(t) for t in texts])


class ConstrainedRewriter:
    """
    For CI-style structured prompts with extractable parameters.
    Two-pass approach:
    1. Extract and translate unique parameter values → translation dictionary
    2. Rewrite full prompts constrained by pre-translated parameters
    """

    def __init__(self, llm_client: Any):
        self.client = llm_client

    def _batch_translate_system_prompt(self, dialect_id: str) -> str:
        config = AVAILABLE_DIALECTS[dialect_id]
        return (
            config["system_prompt"].rstrip(". ")
            + ". For the following list of terms, output one translation or equivalent per line, in the same order. "
            "Output ONLY the translated lines, no numbering or extra text."
        )

    async def build_translation_dict(
        self,
        parameter_values: dict[str, list[str]],
        dialect_id: str,
    ) -> dict[str, dict[str, str]]:
        """
        Pass 1: Translate each unique parameter value.
        Batches values to minimize API calls (send list of values, get list back).
        Returns: {"sender": {"John": "Juan", "Maria": "María"}, ...}
        """
        result: dict[str, dict[str, str]] = {}
        system_prompt = self._batch_translate_system_prompt(dialect_id)

        for param_name, values in parameter_values.items():
            unique_ordered = list(dict.fromkeys(values))  # preserve order, dedupe
            if not unique_ordered:
                result[param_name] = {}
                continue

            batch_prompt = "\n".join(unique_ordered)
            response = await self.client.query(
                prompt=batch_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
            )

            if response.get("error"):
                # On error, map each original to itself so downstream still runs
                result[param_name] = {v: v for v in unique_ordered}
                continue

            raw = (response.get("raw_response") or "").strip()
            translated_lines = [line.strip() for line in raw.split("\n") if line.strip()]
            # Align by index; if counts differ, use original where missing
            result[param_name] = {}
            for i, orig in enumerate(unique_ordered):
                result[param_name][orig] = (
                    translated_lines[i] if i < len(translated_lines) else orig
                )

        return result

    async def rewrite_constrained(
        self,
        text: str,
        translation_dict: dict[str, dict[str, str]],
        dialect_id: str,
    ) -> dict:
        """
        Pass 2: Rewrite the full text, but constrain it to use the pre-translated parameter values.
        The system prompt includes the translation dictionary and instructs the LLM to use those exact translations.
        """
        constraint_text = "Use these exact translations for specific terms:\n"
        for param, translations in translation_dict.items():
            for original, translated in translations.items():
                constraint_text += f'  "{original}" → "{translated}"\n'

        config = AVAILABLE_DIALECTS[dialect_id]
        system_prompt = config["system_prompt"] + "\n\n" + constraint_text

        response = await self.client.query(
            prompt=text,
            system_prompt=system_prompt,
            temperature=0.3,
        )

        return {
            "original": text,
            "rewritten": response.get("raw_response") or "",
            "dialect": dialect_id,
            "success": response.get("error") is None,
            "error": response.get("error"),
        }

    async def rewrite_batch_constrained(
        self,
        prompts: list[dict],
        parameter_columns: list[str],
        dialect_id: str,
        max_concurrent: int = 5,
    ) -> list[dict]:
        """Full pipeline: build dict → rewrite all prompts."""
        # Step 1: Extract unique values per parameter column
        parameter_values: dict[str, list[str]] = {col: [] for col in parameter_columns}
        for p in prompts:
            for col in parameter_columns:
                val = p.get(col)
                if val is not None and str(val).strip():
                    parameter_values[col].append(str(val).strip())

        # Step 2: Build translation dict (one batch call per column)
        translation_dict = await self.build_translation_dict(
            parameter_values, dialect_id
        )

        # Step 3: Rewrite each prompt with constraints
        semaphore = asyncio.Semaphore(max_concurrent)
        texts = [p.get("text", "") for p in prompts]

        async def one(i: int) -> dict:
            async with semaphore:
                return await self.rewrite_constrained(
                    texts[i], translation_dict, dialect_id
                )

        return await asyncio.gather(*[one(i) for i in range(len(prompts))])
