"""
Startup utilities: load grammar and typo transforms and report feature counts.
"""

import logging

logger = logging.getLogger(__name__)


def ensure_transforms_loaded() -> None:
    """Import grammar and typo transform modules to trigger registration."""
    import engine.grammar.transforms  # noqa: F401
    import engine.typos.registry  # noqa: F401


def get_feature_counts() -> tuple[int, int]:
    """Return (grammar_feature_count, typo_feature_count)."""
    from engine.grammar.registry import GRAMMAR_REGISTRY
    from engine.typos.registry import TYPO_REGISTRY
    return len(GRAMMAR_REGISTRY), len(TYPO_REGISTRY)
