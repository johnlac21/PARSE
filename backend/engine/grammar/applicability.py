"""
Applicability checking for grammar features.

Provides batch applicability checking across all prompts and all features.
Ensure transforms are loaded so GRAMMAR_REGISTRY features have applicability_check.
"""

from __future__ import annotations

import pandas as pd

from engine.grammar.registry import GRAMMAR_REGISTRY

# Trigger registration of transform/applicability_check for features from JSON
try:
    import engine.grammar.transforms  # noqa: F401
except Exception:
    pass


def check_applicability(text: str, feature_id: str) -> dict:
    """
    Check whether a single grammar feature applies to the given text.

    Args:
        text: Input text (e.g. a prompt).
        feature_id: Registered feature id.

    Returns:
        Dict with keys: applicable (bool), match_count (int), match_positions (list), reason (str).

    Raises:
        ValueError: If feature_id is not in GRAMMAR_REGISTRY.
    """
    if feature_id not in GRAMMAR_REGISTRY:
        raise ValueError(f"Grammar feature not registered: {feature_id!r}")
    feature = GRAMMAR_REGISTRY[feature_id]
    if feature.applicability_check is None:
        return {
            "applicable": False,
            "match_count": 0,
            "match_positions": [],
            "reason": "no applicability check registered",
        }
    return feature.applicability_check(text)


def check_all_applicability(text: str) -> dict[str, dict]:
    """
    For a single text, check applicability of all registered features.

    Args:
        text: Input text (e.g. a prompt).

    Returns:
        Mapping feature_id -> applicability result dict (applicable, match_count, match_positions, reason).
    """
    result: dict[str, dict] = {}
    for feature_id in GRAMMAR_REGISTRY:
        feature = GRAMMAR_REGISTRY[feature_id]
        if feature.applicability_check is None:
            result[feature_id] = {
                "applicable": False,
                "match_count": 0,
                "match_positions": [],
                "reason": "no applicability check registered",
            }
        else:
            result[feature_id] = feature.applicability_check(text)
    return result


def batch_check_applicability(texts: list[str], feature_ids: list[str]) -> dict:
    """
    For a list of prompts and a list of feature IDs, compute applicability matrix and summary.

    Args:
        texts: List of prompt texts.
        feature_ids: List of registered feature IDs to check.

    Returns:
        Dict with:
          - "matrix": {feature_id: {prompt_index: match_count, ...}, ...}
          - "summary": {feature_id: {total_applicable, total_prompts, applicability_rate, total_matches}, ...}
    """
    n_prompts = len(texts)
    matrix: dict[str, dict[int, int]] = {fid: {} for fid in feature_ids}
    for fid in feature_ids:
        if fid not in GRAMMAR_REGISTRY:
            raise ValueError(f"Grammar feature not registered: {fid!r}")
        feature = GRAMMAR_REGISTRY[fid]
        check = feature.applicability_check
        for i, text in enumerate(texts):
            if check is None:
                matrix[fid][i] = 0
            else:
                res = check(text)
                matrix[fid][i] = res.get("match_count", 0)

    summary: dict[str, dict] = {}
    for fid in feature_ids:
        counts = matrix[fid]
        total_matches = sum(counts.values())
        total_applicable = sum(1 for c in counts.values() if c > 0)
        summary[fid] = {
            "total_applicable": total_applicable,
            "total_prompts": n_prompts,
            "applicability_rate": total_applicable / n_prompts if n_prompts else 0.0,
            "total_matches": total_matches,
        }

    return {
        "matrix": matrix,
        "summary": summary,
    }


def get_applicability_matrix_df(texts: list[str], feature_ids: list[str]) -> pd.DataFrame:
    """
    Return a pandas DataFrame: rows = prompt indices, columns = feature IDs, values = match counts.

    Useful for heatmap visualization.

    Args:
        texts: List of prompt texts.
        feature_ids: List of registered feature IDs.

    Returns:
        DataFrame with index = range(len(texts)), columns = feature_ids, values = match_count.
    """
    batch = batch_check_applicability(texts, feature_ids)
    matrix = batch["matrix"]
    # Build row per prompt_index, col per feature_id
    data: dict[str, list[int]] = {fid: [] for fid in feature_ids}
    n = len(texts)
    for fid in feature_ids:
        row = matrix[fid]
        data[fid] = [row.get(i, 0) for i in range(n)]
    return pd.DataFrame(data, index=range(n))


def suggest_features(
    texts: list[str],
    min_applicability: float = 0.1,
) -> list[dict]:
    """
    Check all registered features against all texts; return features sorted by applicability rate.

    Filters out features with applicability_rate < min_applicability.

    Args:
        texts: List of prompt texts.
        min_applicability: Minimum applicability rate (0..1) to include a feature.

    Returns:
        List of dicts: feature_id, name, applicability_rate, total_applicable, total_prompts.
    """
    if not texts:
        return []
    feature_ids = list(GRAMMAR_REGISTRY.keys())
    if not feature_ids:
        return []
    batch = batch_check_applicability(texts, feature_ids)
    summary = batch["summary"]
    registry = GRAMMAR_REGISTRY
    total_prompts = len(texts)
    out: list[dict] = []
    for fid in feature_ids:
        s = summary[fid]
        rate = s["applicability_rate"]
        if rate < min_applicability:
            continue
        name = registry[fid].name if fid in registry else fid
        out.append({
            "feature_id": fid,
            "name": name,
            "applicability_rate": rate,
            "total_applicable": s["total_applicable"],
            "total_prompts": total_prompts,
        })
    out.sort(key=lambda x: x["applicability_rate"], reverse=True)
    return out
