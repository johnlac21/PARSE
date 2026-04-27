"""Grammar feature registry, transforms, and applicability."""

from engine.grammar.registry import GrammarFeature, GRAMMAR_REGISTRY
from engine.grammar.transforms import apply_grammar
from engine.grammar.applicability import (
    check_applicability,
    check_all_applicability,
    batch_check_applicability,
    get_applicability_matrix_df,
    suggest_features,
)

__all__ = [
    "GrammarFeature",
    "GRAMMAR_REGISTRY",
    "apply_grammar",
    "check_applicability",
    "check_all_applicability",
    "batch_check_applicability",
    "get_applicability_matrix_df",
    "suggest_features",
]
