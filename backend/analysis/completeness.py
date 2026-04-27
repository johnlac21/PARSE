"""
Completeness analysis: valid/invalid/refusals/empty per variant per model.
"""

import re
from typing import Any, Dict

import pandas as pd

# Refusal patterns (case-insensitive) in raw_response
REFUSAL_PATTERNS = [
    r"\bI cannot\b",
    r"\bI'm sorry\b",
    r"\bI am sorry\b",
    r"\bAs an AI\b",
    r"\bas an ai\b",
    r"\bI don't think\b",
    r"\bnot appropriate\b",
    r"\bcannot (assist|help|provide|answer)\b",
    r"\bunable to\b",
    r"\bcan't (assist|help|provide|answer)\b",
    r"\bagainst my\b",
    r"\bpolicy (does not allow|prevents)\b",
]

_refusal_re = re.compile("|".join(f"(?:{p})" for p in REFUSAL_PATTERNS), re.IGNORECASE)


def _is_refusal(raw: str) -> bool:
    if not raw or not isinstance(raw, str):
        return False
    return bool(_refusal_re.search(raw.strip()))


def run_completeness_analysis(results_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze response completeness per variant per model.

    Expects columns: model_id, variant, raw_response, parsed_index (or is_valid).
    Valid = has parsed_index not null (or is_valid True if present).
    Empty = missing or empty raw_response.
    Refusals = detected via refusal patterns in raw_response.

    Returns:
    {
        "model_id": {
            "variant_id": {
                "total": int,
                "valid": int,
                "invalid": int,
                "refusals": int,
                "empty": int,
                "valid_rate": float,
                "refusal_rate": float
            }
        }
    }
    """
    required = {"model_id", "variant"}
    if not required.issubset(results_df.columns):
        missing = required - set(results_df.columns)
        raise ValueError(f"results_df missing columns: {missing}")

    if "raw_response" not in results_df.columns:
        results_df = results_df.copy()
        results_df["raw_response"] = ""

    out: Dict[str, Any] = {}

    for model_id, g_model in results_df.groupby("model_id"):
        out[model_id] = {}
        for variant_id, g in g_model.groupby("variant"):
            total = len(g)
            raw = g["raw_response"].fillna("").astype(str)
            empty = (raw.str.strip() == "").sum()
            refusals = raw.apply(_is_refusal).sum()

            if "parsed_index" in g.columns:
                valid = g["parsed_index"].notna().sum()
            elif "is_valid" in g.columns:
                valid = (g["is_valid"].fillna(0).astype(int) == 1).sum()
            else:
                valid = (total - empty - refusals)
                valid = max(0, valid)

            invalid = total - valid
            valid_rate = (valid / total) if total else 0.0
            refusal_rate = (refusals / total) if total else 0.0

            out[model_id][variant_id] = {
                "total": int(total),
                "valid": int(valid),
                "invalid": int(invalid),
                "refusals": int(refusals),
                "empty": int(empty),
                "valid_rate": round(valid_rate, 4),
                "refusal_rate": round(refusal_rate, 4),
            }

    return out
