#!/usr/bin/env python3
"""
Generate a LaTeX appendix longtable from shared/grammar_features.json.
Output: name, example_std, example_var (no ID); sorted by id; LaTeX-special chars escaped.
Arrows "->" in names/examples are converted to \\rightarrow for LaTeX.
"""

import json
from pathlib import Path

# Project root: scripts/ -> parent
ROOT = Path(__file__).resolve().parent.parent
GRAMMAR_JSON = ROOT / "shared" / "grammar_features.json"
OUTPUT_TEX = ROOT / "appendix_grammar_features.tex"


def escape_latex(s: str) -> str:
    r"""Escape LaTeX special characters: \ { } % $ # & _ ~ ^"""
    if not s:
        return s
    # Order matters: backslash first
    s = s.replace("\\", "\\textbackslash{}")
    s = s.replace("{", "\\{")
    s = s.replace("}", "\\}")
    s = s.replace("%", "\\%")
    s = s.replace("$", "\\$")
    s = s.replace("#", "\\#")
    s = s.replace("&", "\\&")
    s = s.replace("_", "\\_")
    s = s.replace("~", "\\textasciitilde{}")
    s = s.replace("^", "\\textasciicircum{}")
    return s


def arrow_latex(s: str) -> str:
    """Replace ASCII arrow -> with LaTeX \\rightarrow so it renders correctly."""
    return s.replace(" -> ", " $\\rightarrow$ ")


def main() -> None:
    with open(GRAMMAR_JSON, encoding="utf-8") as f:
        data = json.load(f)
    features = data["features"]
    # Sort by id ascending
    features = sorted(features, key=lambda x: x["id"])

    lines = [
        "% Grammar features appendix table (generated from shared/grammar_features.json)",
        "% Paste into thesis appendix. Required: \\usepackage{longtable}, \\usepackage{array}, \\usepackage{booktabs}.",
        "",
        "\\setlength{\\tabcolsep}{3pt}",
        "\\small",
        "\\begin{longtable}{",
        "  >{\\raggedright\\arraybackslash}p{3.2cm}",
        "  >{\\raggedright\\arraybackslash}p{4.8cm}",
        "  >{\\raggedright\\arraybackslash}p{4.8cm}",
        "}",
        "\\toprule",
        "\\textbf{Name} & \\textbf{Example (standard)} & \\textbf{Example (variant)} \\\\",
        "\\midrule",
        "\\endfirsthead",
        "",
        "\\multicolumn{3}{l}{\\textit{Continued from previous page}} \\\\",
        "\\toprule",
        "\\textbf{Name} & \\textbf{Example (standard)} & \\textbf{Example (variant)} \\\\",
        "\\midrule",
        "\\endhead",
        "",
        "\\midrule",
        "\\multicolumn{3}{r}{\\textit{Continued on next page}} \\\\",
        "\\endfoot",
        "",
        "\\bottomrule",
        "\\endlastfoot",
        "",
    ]

    for f in features:
        name = arrow_latex(escape_latex(f["name"]))
        ex_std = arrow_latex(escape_latex(f["example_std"]))
        ex_var = arrow_latex(escape_latex(f["example_var"]))
        row = f"{name} & {ex_std} & {ex_var} \\\\"
        lines.append(row)

    lines.extend([
        "",
        "\\end{longtable}",
        "\\setlength{\\tabcolsep}{6pt}  % restore default",
    ])

    with open(OUTPUT_TEX, "w", encoding="utf-8") as out:
        out.write("\n".join(lines))

    print(f"Wrote {len(features)} rows to {OUTPUT_TEX}")


if __name__ == "__main__":
    main()
