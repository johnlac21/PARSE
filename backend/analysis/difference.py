"""
Difference analysis: Linear Probability Model for P(response changed).
"""

import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

from typing import Any, Dict


def _significance(p_value: float) -> str:
    if p_value < 0.001:
        return "***"
    if p_value < 0.01:
        return "**"
    if p_value < 0.05:
        return "*"
    return ""


def run_difference_lpm(
    results_df: pd.DataFrame,
    baseline_variant: str = "standard",
) -> Dict[str, Any]:
    """
    Linear Probability Model: P(response changed) = β₀ + ε

    For each model and each variant:
    1. Compare each variant's parsed_index to the baseline's parsed_index for the same prompt
    2. Create binary outcome: 1 if different, 0 if same
    3. Run OLS regression: y ~ 1 (intercept only)
    4. The intercept = difference rate

    Input DataFrame should have columns: prompt_id, variant, model_id, parsed_index

    Returns:
    {
        "model_id": {
            "variant_id": {
                "difference_rate": float,
                "se": float,
                "t_stat": float,
                "p_value": float,
                "n_obs": int,
                "ci_lower": float,
                "ci_upper": float,
                "significance": str
            }
        }
    }
    """
    required = {"prompt_id", "variant", "model_id", "parsed_index"}
    if not required.issubset(results_df.columns):
        missing = required - set(results_df.columns)
        raise ValueError(f"results_df missing columns: {missing}")

    out: Dict[str, Any] = {}

    # Pivot so we have baseline parsed_index per (prompt_id, model_id)
    baseline = results_df.loc[
        results_df["variant"] == baseline_variant,
        ["prompt_id", "model_id", "parsed_index"],
    ].rename(columns={"parsed_index": "baseline_parsed_index"})

    # Merge variant rows with baseline
    non_baseline = results_df[results_df["variant"] != baseline_variant].copy()
    merged = non_baseline.merge(
        baseline,
        on=["prompt_id", "model_id"],
        how="inner",
    )

    if merged.empty:
        return out

    # Drop rows where either parsed_index or baseline is NaN (can't compare)
    merged = merged.dropna(subset=["parsed_index", "baseline_parsed_index"])

    merged["changed"] = (merged["parsed_index"] != merged["baseline_parsed_index"]).astype(int)

    for model_id, g_model in merged.groupby("model_id"):
        out[model_id] = {}
        for variant_id, g in g_model.groupby("variant"):
            y = g["changed"].values
            n_obs = len(y)

            # Edge cases
            if n_obs < 2:
                out[model_id][variant_id] = {
                    "difference_rate": float(np.mean(y)) if n_obs else 0.0,
                    "se": 0.0,
                    "t_stat": 0.0,
                    "p_value": 1.0,
                    "n_obs": n_obs,
                    "ci_lower": 0.0,
                    "ci_upper": 1.0,
                    "significance": "",
                }
                continue

            all_same = y.min() == y.max()
            if all_same:
                rate = float(y[0])
                se = 0.0
                t_stat = 0.0 if rate == 0 else np.inf
                p_value = 0.0 if rate in (0.0, 1.0) else 1.0
                ci_lower = rate
                ci_upper = rate
            else:
                X = add_constant(np.ones((n_obs, 1)))
                model = OLS(y, X).fit()
                rate = float(model.params[0])
                se = float(model.bse[0])
                t_stat = float(model.tvalues[0])
                p_value = float(model.pvalues[0])
                ci = model.conf_int(alpha=0.05)
                ci_arr = getattr(ci, "values", ci)
                ci_lower = float(ci_arr[0, 0])
                ci_upper = float(ci_arr[0, 1])

            out[model_id][variant_id] = {
                "difference_rate": rate,
                "se": se,
                "t_stat": t_stat,
                "p_value": p_value,
                "n_obs": n_obs,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "significance": _significance(p_value) if not all_same else "",
            }

    return out
