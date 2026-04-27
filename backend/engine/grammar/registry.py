"""
Grammar feature dataclass and GRAMMAR_REGISTRY.

Maps feature IDs to GrammarFeature definitions. Features can be loaded from
shared/grammar_features.json; transform and applicability_check are registered separately.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

# Project root: backend/engine/grammar/registry.py -> 4 levels up
_DEFAULT_GRAMMAR_JSON_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "shared" / "grammar_features.json"
)

VALID_CATEGORIES = frozenset({
    "morphosyntactic",
    "verbal",
    "nominal",
    "negation",
    "phonological",
    "pronominal",
    "pronoun",  # alias used in grammar_features.json
})


@dataclass
class GrammarFeature:
    """Describes a grammar feature: metadata, examples, and optional transform/check."""

    id: str
    name: str
    description: str
    example_std: str
    example_var: str
    category: str  # one of: morphosyntactic, verbal, nominal, negation, phonological, pronominal
    dialects: list[str]
    requires_pos_tags: bool
    tier: int
    source: str
    applicability_check: Callable[[str], dict] | None = None
    transform: Callable[[str], str] | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("GrammarFeature.id cannot be empty")


GRAMMAR_REGISTRY: dict[str, GrammarFeature] = {}


def register(feature: GrammarFeature) -> None:
    """Add a grammar feature to the registry. Overwrites existing entry with same id."""
    if not feature.id:
        raise ValueError("Cannot register a GrammarFeature with empty id")
    GRAMMAR_REGISTRY[feature.id] = feature
    logger.debug("Registered grammar feature: %s", feature.id)


def load_features_from_json(path: str | Path | None = None) -> int:
    """
    Read grammar_features.json and create GrammarFeature objects (without
    transform or applicability_check). Adds them to GRAMMAR_REGISTRY.
    Returns the number of features loaded.
    """
    resolved = Path(path) if path is not None else _DEFAULT_GRAMMAR_JSON_PATH
    resolved = resolved.resolve()

    if not resolved.exists():
        logger.error("Grammar features file not found: %s", resolved)
        raise FileNotFoundError(f"Grammar features file not found: {resolved}")

    try:
        raw = resolved.read_text(encoding="utf-8")
    except OSError as e:
        logger.exception("Failed to read grammar features file: %s", resolved)
        raise

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.exception("Invalid JSON in grammar features file: %s", resolved)
        raise

    features_list = data.get("features")
    if not isinstance(features_list, list):
        logger.error("Grammar features file must contain a 'features' array")
        raise ValueError("Grammar features file must contain a 'features' array")

    count = 0
    for i, item in enumerate(features_list):
        if not isinstance(item, dict):
            logger.warning("Skipping non-object at features[%d]", i)
            continue
        try:
            feature = _dict_to_feature(item)
            register(feature)
            count += 1
        except (KeyError, TypeError, ValueError) as e:
            logger.warning("Skipping invalid feature at features[%d]: %s", i, e)
            continue

    logger.info("Loaded %d grammar features from %s", count, resolved)
    return count


def _dict_to_feature(obj: dict) -> GrammarFeature:
    """Build a GrammarFeature from a JSON object (no transform/applicability_check)."""
    return GrammarFeature(
        id=_require_str(obj, "id"),
        name=_require_str(obj, "name"),
        description=_require_str(obj, "description"),
        example_std=_require_str(obj, "example_std"),
        example_var=_require_str(obj, "example_var"),
        category=_require_str(obj, "category"),
        dialects=_require_list_str(obj, "dialects"),
        requires_pos_tags=_require_bool(obj, "requires_pos_tags"),
        tier=_require_int(obj, "tier"),
        source=_require_str(obj, "source"),
        applicability_check=None,
        transform=None,
    )


def _require_str(obj: dict, key: str) -> str:
    if key not in obj:
        raise KeyError(f"Missing required field: {key}")
    v = obj[key]
    if not isinstance(v, str):
        raise TypeError(f"Field '{key}' must be a string, got {type(v).__name__}")
    return v


def _require_bool(obj: dict, key: str) -> bool:
    if key not in obj:
        raise KeyError(f"Missing required field: {key}")
    v = obj[key]
    if not isinstance(v, bool):
        raise TypeError(f"Field '{key}' must be a bool, got {type(v).__name__}")
    return v


def _require_int(obj: dict, key: str) -> int:
    if key not in obj:
        raise KeyError(f"Missing required field: {key}")
    v = obj[key]
    if not isinstance(v, int):
        raise TypeError(f"Field '{key}' must be an int, got {type(v).__name__}")
    return v


def _require_list_str(obj: dict, key: str) -> list[str]:
    if key not in obj:
        raise KeyError(f"Missing required field: {key}")
    v = obj[key]
    if not isinstance(v, list):
        raise TypeError(f"Field '{key}' must be a list, got {type(v).__name__}")
    for i, el in enumerate(v):
        if not isinstance(el, str):
            raise TypeError(f"Field '{key}'[{i}] must be a string, got {type(el).__name__}")
    return v


def get_feature(feature_id: str) -> GrammarFeature:
    """Return the GrammarFeature for the given id. Raises KeyError if not registered."""
    if feature_id not in GRAMMAR_REGISTRY:
        raise KeyError(f"Grammar feature not registered: {feature_id!r}")
    return GRAMMAR_REGISTRY[feature_id]


def get_all_features() -> list[GrammarFeature]:
    """Return all registered grammar features (order not guaranteed)."""
    return list(GRAMMAR_REGISTRY.values())


def get_features_by_category(category: str) -> list[GrammarFeature]:
    """Return all registered features whose category equals the given string."""
    return [f for f in GRAMMAR_REGISTRY.values() if f.category == category]


def get_features_by_tier(tier: int) -> list[GrammarFeature]:
    """Return all registered features with the given tier."""
    return [f for f in GRAMMAR_REGISTRY.values() if f.tier == tier]
