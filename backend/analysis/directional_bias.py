"""
Directional bias analysis: signed difference vs baseline (parsed_index as score).
"""

import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

from typing import Any, Dict, Literal


def _significance(p_value: float) -> str:
    if p_value < 0.001:
        return "***"
    if p_value < 0.01:
        return "**"
    if p_value < 0.05:
        return "*"
    return ""


def run_directional_bias(
    results_df: pd.DataFrame,
    baseline_variant: str = "standard",
) -> Dict[str, Any]:
    """
    Signed Difference Regression: E[score_variant - score_baseline] = β₀

    For each model and each variant:
    1. Compute difference: variant_score - baseline_score for each prompt
    2. Run OLS: diff ~ 1
    3. Positive β₀ = variant produces higher/more permissive scores
    4. Negative β₀ = variant produces lower/more restrictive scores

    Input DataFrame should have columns: prompt_id, variant, model_id, parsed_index
    (parsed_index is used as the numeric score).

    Returns same structure as difference but with:
    - "mean_difference": float (β₀)
    - "direction": "higher" | "lower" | "neutral"
    """
    required = {"prompt_id", "variant", "model_id", "parsed_index"}
    if not required.issubset(results_df.columns):
        missing = required - set(results_df.columns)
        raise ValueError(f"results_df missing columns: {missing}")

    out: Dict[str, Any] = {}

    baseline = results_df.loc[
        results_df["variant"] == baseline_variant,
        ["prompt_id", "model_id", "parsed_index"],
    ].rename(columns={"parsed_index": "baseline_score"})

    non_baseline = results_df[results_df["variant"] != baseline_variant].copy()
    merged = non_baseline.merge(
        baseline,
        on=["prompt_id", "model_id"],
        how="inner",
    )

    if merged.empty:
        return out

    merged = merged.dropna(subset=["parsed_index", "baseline_score"])
    merged["diff"] = merged["parsed_index"].astype(float) - merged["baseline_score"].astype(float)

    for model_id, g_model in merged.groupby("model_id"):
        out[model_id] = {}
        for variant_id, g in g_model.groupby("variant"):
            y = g["diff"].values
            n_obs = len(y)

            if n_obs < 2:
                mean_diff = float(np.mean(y)) if n_obs else 0.0
                direction: Literal["higher", "lower", "neutral"] = (
                    "higher" if mean_diff > 0 else ("lower" if mean_diff < 0 else "neutral")
                )
                out[model_id][variant_id] = {
                    "mean_difference": mean_diff,
                    "se": 0.0,
                    "t_stat": 0.0,
                    "p_value": 1.0,
                    "n_obs": n_obs,
                    "ci_lower": mean_diff,
                    "ci_upper": mean_diff,
                    "significance": "",
                    "direction": direction,
                }
                continue

            X = add_constant(np.ones((n_obs, 1)))
            model = OLS(y, X).fit()
            mean_diff = float(model.params[0])
            se = float(model.bse[0])
            t_stat = float(model.tvalues[0])
            p_value = float(model.pvalues[0])
            ci = model.conf_int(alpha=0.05)
            ci_arr = getattr(ci, "values", ci)
            ci_lower = float(ci_arr[0, 0])
            ci_upper = float(ci_arr[0, 1])

            if mean_diff > 0:
                direction = "higher"
            elif mean_diff < 0:
                direction = "lower"
            else:
                direction = "neutral"

            out[model_id][variant_id] = {
                "mean_difference": mean_diff,
                "se": se,
                "t_stat": t_stat,
                "p_value": p_value,
                "n_obs": n_obs,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "significance": _significance(p_value),
                "direction": direction,
            }

    return out
