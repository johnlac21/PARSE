"""
Export analysis results to LaTeX, CSV, and JSON.

Table types: "difference" (LPM rates per variant per model), "directional_bias"
(mean difference vs baseline), "completeness" (valid/total and valid_rate).
Formats: latex (booktabs-style tables), csv (flat rows), json (nested dict).
Entry points: results_to_latex(), results_to_csv(), results_to_json().
"""

import csv
import io
from typing import Any, Dict, List, Tuple


def _fmt(x: float, decimals: int = 3) -> str:
    if x is None:
        return ""
    return f"{x:.{decimals}f}"


def _latex_escape(s: str) -> str:
    """Escape underscores for LaTeX."""
    return (s or "").replace("_", "\\_")


def _significance_stars(p_value: float) -> str:
    """*** p<0.001, ** p<0.01, * p<0.05"""
    if p_value is None:
        return ""
    if p_value < 0.001:
        return "***"
    if p_value < 0.01:
        return "**"
    if p_value < 0.05:
        return "*"
    return ""


# --- Difference: variant-rows, model-columns; coef row then (SE) row ---


def _difference_variant_model_grid(
    results: Dict[str, Any],
) -> Tuple[List[str], List[str], Dict[str, Dict[str, Dict[str, Any]]]]:
    """Returns (model_ids, variant_ids, grid[variant][model] = {rate, se, sig, n_obs})."""
    model_ids: List[str] = []
    variant_ids: List[str] = []
    grid: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for model_id, variants in results.items():
        if not isinstance(variants, dict):
            continue
        if model_id not in model_ids:
            model_ids.append(model_id)
        for variant_id, v in variants.items():
            if not isinstance(v, dict):
                continue
            if variant_id not in variant_ids:
                variant_ids.append(variant_id)
            if variant_id not in grid:
                grid[variant_id] = {}
            grid[variant_id][model_id] = {
                "value": v.get("difference_rate"),
                "se": v.get("se"),
                "sig": v.get("significance", ""),
                "n_obs": v.get("n_obs", 0),
            }
    return model_ids, variant_ids, grid


def to_latex_difference(results: Dict[str, Any]) -> str:
    """
    Generate LaTeX table matching academic paper format:
    Variant column, then Model 1, Model 2, ...; each variant has coefficient row then (SE) row.
    Significance: *** p<0.001, ** p<0.01, * p<0.05. N observation count at bottom.
    """
    model_ids, variant_ids, grid = _difference_variant_model_grid(results)
    if not model_ids or not variant_ids:
        buf = io.StringIO()
        buf.write("\\begin{table}[htbp]\n\\centering\n")
        buf.write("\\caption{Difference Analysis (Linear Probability Model)}\n")
        buf.write("\\begin{tabular}{lc}\n\\toprule\nVariant & (no data) \\\\\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")
        return buf.getvalue()

    buf = io.StringIO()
    buf.write("\\begin{table}[htbp]\n\\centering\n")
    buf.write("\\caption{Difference Analysis (Linear Probability Model)}\n")
    col_spec = "l" + "c" * len(model_ids)
    buf.write(f"\\begin{{tabular}}{{{col_spec}}}\n")
    buf.write("\\toprule\n")
    header_cells = ["Variant"] + [_latex_escape(m) for m in model_ids]
    buf.write(" & ".join(header_cells) + " \\\\\n")
    buf.write("\\midrule\n")

    for variant_id in variant_ids:
        row_data = grid.get(variant_id, {})
        # Coefficient row
        cells = [_latex_escape(variant_id)]
        for model_id in model_ids:
            d = row_data.get(model_id, {})
            val = d.get("value")
            sig = d.get("sig", "")
            if val is not None:
                cells.append(_fmt(val, 3) + sig)
            else:
                cells.append("")
        buf.write(" & ".join(cells) + " \\\\\n")
        # SE row
        cells_se = [""]
        for model_id in model_ids:
            d = row_data.get(model_id, {})
            se = d.get("se")
            if se is not None:
                cells_se.append("(" + _fmt(se, 3) + ")")
            else:
                cells_se.append("")
        buf.write(" & ".join(cells_se) + " \\\\\n")

    # N row
    buf.write("\\midrule\n")
    n_cells = ["$N$"]
    for model_id in model_ids:
        n_val = 0
        for variant_id in variant_ids:
            d = grid.get(variant_id, {}).get(model_id, {})
            n_val = d.get("n_obs", 0)
            if n_val:
                break
        n_cells.append(str(n_val))
    buf.write(" & ".join(n_cells) + " \\\\\n")
    buf.write("\\bottomrule\n")
    buf.write("\\end{tabular}\n\\end{table}\n")
    return buf.getvalue()


# --- Directional bias: same layout with mean diff and direction ---


def _directional_variant_model_grid(
    results: Dict[str, Any],
) -> Tuple[List[str], List[str], Dict[str, Dict[str, Dict[str, Any]]]]:
    """Returns (model_ids, variant_ids, grid[variant][model] = {value, se, sig, direction, n_obs})."""
    model_ids = []
    variant_ids = []
    grid: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for model_id, variants in results.items():
        if not isinstance(variants, dict):
            continue
        if model_id not in model_ids:
            model_ids.append(model_id)
        for variant_id, v in variants.items():
            if not isinstance(v, dict):
                continue
            if variant_id not in variant_ids:
                variant_ids.append(variant_id)
            if variant_id not in grid:
                grid[variant_id] = {}
            grid[variant_id][model_id] = {
                "value": v.get("mean_difference"),
                "se": v.get("se"),
                "sig": v.get("significance", ""),
                "direction": v.get("direction", ""),
                "n_obs": v.get("n_obs", 0),
            }
    return model_ids, variant_ids, grid


def to_latex_directional_bias(results: Dict[str, Any]) -> str:
    """
    Same academic format: Variant | Model 1 | Model 2 | ... with mean differences and direction.
    """
    model_ids, variant_ids, grid = _directional_variant_model_grid(results)
    if not model_ids or not variant_ids:
        buf = io.StringIO()
        buf.write("\\begin{table}[htbp]\n\\centering\n")
        buf.write("\\caption{Directional Bias Analysis}\n")
        buf.write("\\begin{tabular}{lc}\n\\toprule\nVariant & (no data) \\\\\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")
        return buf.getvalue()

    buf = io.StringIO()
    buf.write("\\begin{table}[htbp]\n\\centering\n")
    buf.write("\\caption{Directional Bias Analysis}\n")
    col_spec = "l" + "c" * len(model_ids)
    buf.write(f"\\begin{{tabular}}{{{col_spec}}}\n")
    buf.write("\\toprule\n")
    header_cells = ["Variant"] + [_latex_escape(m) for m in model_ids]
    buf.write(" & ".join(header_cells) + " \\\\\n")
    buf.write("\\midrule\n")

    for variant_id in variant_ids:
        row_data = grid.get(variant_id, {})
        cells = [_latex_escape(variant_id)]
        for model_id in model_ids:
            d = row_data.get(model_id, {})
            val = d.get("value")
            sig = d.get("sig", "")
            if val is not None:
                cells.append(_fmt(val, 3) + sig)
            else:
                cells.append("")
        buf.write(" & ".join(cells) + " \\\\\n")
        cells_se = [""]
        for model_id in model_ids:
            d = row_data.get(model_id, {})
            se = d.get("se")
            if se is not None:
                cells_se.append("(" + _fmt(se, 3) + ")")
            else:
                cells_se.append("")
        buf.write(" & ".join(cells_se) + " \\\\\n")

    buf.write("\\midrule\n")
    n_cells = ["$N$"]
    for model_id in model_ids:
        n_val = 0
        for variant_id in variant_ids:
            d = grid.get(variant_id, {}).get(model_id, {})
            n_val = d.get("n_obs", 0)
            if n_val:
                break
        n_cells.append(str(n_val))
    buf.write(" & ".join(n_cells) + " \\\\\n")
    buf.write("\\bottomrule\n")
    buf.write("\\end{tabular}\n\\end{table}\n")
    return buf.getvalue()


# --- Completeness: simple table with counts and percentages ---


def _flatten_completeness(data: Dict[str, Any]) -> List[Tuple[str, str, int, int, int, int, int, str, str]]:
    rows: List[Tuple[str, str, int, int, int, int, int, str, str]] = []
    for model_id, variants in data.items():
        if not isinstance(variants, dict):
            continue
        for variant_id, v in variants.items():
            if not isinstance(v, dict):
                continue
            rows.append((
                model_id,
                variant_id,
                v.get("total", 0),
                v.get("valid", 0),
                v.get("invalid", 0),
                v.get("refusals", 0),
                v.get("empty", 0),
                _fmt(v.get("valid_rate", 0)),
                _fmt(v.get("refusal_rate", 0)),
            ))
    return rows


def to_latex_completeness(results: Dict[str, Any]) -> str:
    """Simple LaTeX table with counts and percentages."""
    rows = _flatten_completeness(results)
    buf = io.StringIO()
    buf.write("\\begin{table}[htbp]\n\\centering\n")
    buf.write("\\caption{Completeness Analysis}\n")
    buf.write("\\begin{tabular}{l l r r r r r r r}\n")
    buf.write("\\toprule\n")
    buf.write("Model & Variant & Total & Valid & Invalid & Refusals & Empty & Valid rate & Refusal rate \\\\\n")
    buf.write("\\midrule\n")
    for row in rows:
        model_id, variant_id, total, valid, invalid, refusals, empty, vr, rr = row
        buf.write(
            f"{_latex_escape(model_id)} & {_latex_escape(variant_id)} & {total} & {valid} & {invalid} & {refusals} & {empty} & {vr} & {rr} \\\\\n"
        )
    buf.write("\\bottomrule\n")
    buf.write("\\end{tabular}\n\\end{table}\n")
    return buf.getvalue()


# --- CSV: flat rows model,variant,value,se,p_value,significance (and type-specific) ---


def _flatten_difference(data: Dict[str, Any]) -> List[Tuple[str, str, float, float, float, str, int]]:
    out: List[Tuple[str, str, float, float, float, str, int]] = []
    for model_id, variants in data.items():
        if not isinstance(variants, dict):
            continue
        for variant_id, v in variants.items():
            if not isinstance(v, dict):
                continue
            out.append((
                model_id,
                variant_id,
                v.get("difference_rate") if v.get("difference_rate") is not None else 0.0,
                v.get("se") if v.get("se") is not None else 0.0,
                v.get("p_value") if v.get("p_value") is not None else 0.0,
                v.get("significance", ""),
                v.get("n_obs", 0),
            ))
    return out


def _flatten_directional_bias(data: Dict[str, Any]) -> List[Tuple[str, str, float, float, float, str, str, int]]:
    out: List[Tuple[str, str, float, float, float, str, str, int]] = []
    for model_id, variants in data.items():
        if not isinstance(variants, dict):
            continue
        for variant_id, v in variants.items():
            if not isinstance(v, dict):
                continue
            out.append((
                model_id,
                variant_id,
                v.get("mean_difference") if v.get("mean_difference") is not None else 0.0,
                v.get("se") if v.get("se") is not None else 0.0,
                v.get("p_value") if v.get("p_value") is not None else 0.0,
                v.get("significance", ""),
                v.get("direction", ""),
                v.get("n_obs", 0),
            ))
    return out


def to_csv_flat(results: Dict[str, Any], table_type: str) -> str:
    """
    Flatten nested dict into CSV rows.
    Difference/directional_bias: model,variant,value,se,p_value,significance[,direction],n_obs
    Completeness: model,variant,total,valid,invalid,refusals,empty,valid_rate,refusal_rate
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    if table_type == "difference":
        writer.writerow(["model", "variant", "value", "se", "p_value", "significance", "n_obs"])
        for row in _flatten_difference(results):
            writer.writerow(row)
    elif table_type == "directional_bias":
        writer.writerow(["model", "variant", "value", "se", "p_value", "significance", "direction", "n_obs"])
        for row in _flatten_directional_bias(results):
            writer.writerow(row)
    elif table_type == "completeness":
        writer.writerow(["model", "variant", "total", "valid", "invalid", "refusals", "empty", "valid_rate", "refusal_rate"])
        for row in _flatten_completeness(results):
            writer.writerow(row)
    else:
        writer.writerow(["error"])
        writer.writerow([f"Unknown table_type: {table_type}"])
    return buf.getvalue()


# --- JSON for frontend ---


def to_json_frontend(results: Dict[str, Any]) -> Dict[str, Any]:
    """Clean JSON ready for frontend charting (no NaN, consistent types)."""

    def clean(obj: Any) -> Any:
        if obj is None:
            return None
        if isinstance(obj, dict):
            return {str(k): clean(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [clean(x) for x in obj]
        if isinstance(obj, (int, float)):
            if isinstance(obj, float) and (obj != obj):  # NaN
                return None
            return obj
        if isinstance(obj, str):
            return obj
        return str(obj)

    return clean(results)


# --- Legacy aliases for router (router can call to_* directly) ---


def results_to_latex(analysis_results: Dict[str, Any], table_type: str) -> str:
    """Dispatch to the appropriate to_latex_* function."""
    if table_type == "difference":
        return to_latex_difference(analysis_results)
    if table_type == "directional_bias":
        return to_latex_directional_bias(analysis_results)
    if table_type == "completeness":
        return to_latex_completeness(analysis_results)
    return "\\begin{table}[htbp]\n\\centering\nUnknown table type.\\end{table}\n"


def results_to_csv(analysis_results: Dict[str, Any], table_type: str) -> str:
    """Use flat CSV format."""
    return to_csv_flat(analysis_results, table_type)


def results_to_json(analysis_results: Dict[str, Any]) -> Dict[str, Any]:
    """Alias for frontend-ready JSON."""
    return to_json_frontend(analysis_results)
