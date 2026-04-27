"""
Compound variant generation from grammar, typo, and dialect features.

Generates variant combinations from selected features using GRAMMAR_REGISTRY
and TYPO_REGISTRY.
"""

import itertools
import logging
import random
from typing import Any

from engine.grammar.registry import GRAMMAR_REGISTRY
from engine.grammar.transforms import apply_grammar
from engine.typos.registry import TYPO_REGISTRY

logger = logging.getLogger(__name__)

_MAX_GRAMMAR_COMBINATIONS = 10


def _validate_grammar_features(feature_ids: list[str]) -> None:
    """Raise ValueError if any feature_id is not in GRAMMAR_REGISTRY."""
    unknown = [fid for fid in feature_ids if fid not in GRAMMAR_REGISTRY]
    if unknown:
        available = ", ".join(sorted(GRAMMAR_REGISTRY.keys())[:10])
        if len(GRAMMAR_REGISTRY) > 10:
            available += ", ..."
        raise ValueError(
            f"Unknown grammar feature(s): {unknown}. "
            f"Available features include: {available}"
        )


def _validate_typo_features(typo_ids: list[str]) -> None:
    """Raise ValueError if any typo_id is not in TYPO_REGISTRY."""
    unknown = [tid for tid in typo_ids if tid not in TYPO_REGISTRY]
    if unknown:
        available = ", ".join(sorted(TYPO_REGISTRY.keys())[:10])
        if len(TYPO_REGISTRY) > 10:
            available += ", ..."
        raise ValueError(
            f"Unknown typo feature(s): {unknown}. "
            f"Available typo types include: {available}"
        )


def _apply_grammar_sequence(text: str, feature_ids: list[str]) -> str:
    """Apply grammar features in alphabetical order for reproducibility."""
    current = text
    for fid in sorted(feature_ids):
        current = apply_grammar(current, fid)
    return current


def generate_grammar_variants(
    text: str,
    feature_ids: list[str],
    mode: str = "individual",
) -> list[dict]:
    """
    Generate grammar variants from selected feature IDs.

    Modes:
    - individual: one variant per feature (N variants).
    - all_combinations: all 2^N - 1 non-empty subsets (max 10 features).
    - bundle: apply all selected features at once (1 variant).

    Returns list of dicts with variant_id, variant_type, text, features_applied,
    original_text, changes_made.
    """
    if not feature_ids:
        return []

    _validate_grammar_features(feature_ids)

    if mode == "all_combinations" and len(feature_ids) > _MAX_GRAMMAR_COMBINATIONS:
        raise ValueError(
            f"all_combinations mode is limited to at most {_MAX_GRAMMAR_COMBINATIONS} "
            f"features (got {len(feature_ids)}). Use fewer features or switch to "
            "'individual' or 'bundle' mode."
        )

    result: list[dict] = []
    original_text = text

    if mode == "individual":
        for fid in feature_ids:
            transformed = apply_grammar(text, fid)
            result.append({
                "variant_id": fid,
                "variant_type": "grammar",
                "text": transformed,
                "features_applied": [fid],
                "original_text": original_text,
                "changes_made": transformed != original_text,
            })

    elif mode == "all_combinations":
        for r in range(1, len(feature_ids) + 1):
            for combo in itertools.combinations(feature_ids, r):
                ordered = sorted(combo)
                variant_id = "+".join(ordered)
                transformed = _apply_grammar_sequence(text, list(ordered))
                result.append({
                    "variant_id": variant_id,
                    "variant_type": "grammar",
                    "text": transformed,
                    "features_applied": list(ordered),
                    "original_text": original_text,
                    "changes_made": transformed != original_text,
                })

    elif mode == "bundle":
        ordered = sorted(feature_ids)
        variant_id = "+".join(ordered)
        transformed = _apply_grammar_sequence(text, ordered)
        result.append({
            "variant_id": variant_id,
            "variant_type": "grammar",
            "text": transformed,
            "features_applied": ordered,
            "original_text": original_text,
            "changes_made": transformed != original_text,
        })

    else:
        raise ValueError(
            f"Invalid grammar mode: {mode!r}. "
            "Use 'individual', 'all_combinations', or 'bundle'."
        )

    return result


def generate_typo_variants(
    text: str,
    typo_ids: list[str],
    word_p: float = 0.15,
    char_p: float = 0.6,
    seed: int = 42,
) -> list[dict]:
    """
    Generate one variant per typo type (individual only).

    Returns list of dicts with variant_id, variant_type, text, typo_type,
    original_text, seed_used. word_p and char_p are accepted for API compatibility;
    typo transforms use the given seed for reproducibility.
    """
    if not typo_ids:
        return []

    _validate_typo_features(typo_ids)

    result: list[dict] = []
    original_text = text
    random.seed(seed)

    for tid in typo_ids:
        feature = TYPO_REGISTRY[tid]
        # If transform accepts extra args (word_p, char_p, rng), we could pass them
        # here; current TypoFeature.transform is Callable[[str], str]
        try:
            transformed = feature.transform(text)
        except Exception as e:
            logger.warning("Typo transform %s failed: %s", tid, e)
            transformed = text
        result.append({
            "variant_id": tid,
            "variant_type": "typo",
            "text": transformed,
            "typo_type": tid,
            "original_text": original_text,
            "seed_used": seed,
        })

    return result


def generate_all_variants(
    text: str,
    prompt_id: int,
    grammar_features: list[str] = [],
    grammar_mode: str = "individual",
    typo_features: list[str] = [],
    typo_word_p: float = 0.15,
    typo_char_p: float = 0.6,
    seed: int = 42,
    include_cross_combinations: bool = False,
) -> list[dict]:
    """
    Generate all variants for a single prompt.

    Always includes the original as the first entry (variant_id="standard",
    variant_type="original"). Then grammar variants, then typo variants.
    If include_cross_combinations is True, also adds grammar+typo combinations
    (grammar-transformed text with each typo applied on top).
    """
    out: list[dict] = []

    # Original first
    out.append({
        "variant_id": "standard",
        "variant_type": "original",
        "text": text,
        "original_text": text,
        "prompt_id": prompt_id,
    })

    # Grammar variants
    grammar_variants = generate_grammar_variants(text, grammar_features, mode=grammar_mode)
    for v in grammar_variants:
        v["prompt_id"] = prompt_id
        out.append(v)

    # Typo variants (on original text)
    typo_variants = generate_typo_variants(
        text, typo_features, word_p=typo_word_p, char_p=typo_char_p, seed=seed
    )
    for v in typo_variants:
        v["prompt_id"] = prompt_id
        out.append(v)

    # Cross: for each grammar variant text, apply each typo
    if include_cross_combinations and grammar_variants and typo_features:
        _validate_typo_features(typo_features)
        random.seed(seed)
        for gv in grammar_variants:
            base_text = gv["text"]
            base_id = gv["variant_id"]
            for tid in typo_features:
                if tid not in TYPO_REGISTRY:
                    continue
                feature = TYPO_REGISTRY[tid]
                try:
                    cross_text = feature.transform(base_text)
                except Exception as e:
                    logger.warning("Cross typo %s on %s failed: %s", tid, base_id, e)
                    cross_text = base_text
                cross_variant_id = f"{base_id}+{tid}"
                out.append({
                    "variant_id": cross_variant_id,
                    "variant_type": "grammar+typo",
                    "text": cross_text,
                    "features_applied": gv.get("features_applied", []) + [tid],
                    "original_text": text,
                    "prompt_id": prompt_id,
                    "seed_used": seed,
                })

    return out


def generate_batch_variants(
    prompts: list[dict],
    grammar_features: list[str] = [],
    grammar_mode: str = "individual",
    typo_features: list[str] = [],
    typo_word_p: float = 0.15,
    typo_char_p: float = 0.6,
    seed: int = 42,
) -> list[dict]:
    """
    Generate variants for all prompts. Returns a flat list; each entry includes
    prompt_id for tracking. Logs a summary of counts.
    """
    flat: list[dict] = []
    num_prompts = len(prompts)

    for p in prompts:
        prompt_id = p.get("prompt_id")
        prompt_text = p.get("prompt_text", "")
        if prompt_id is None:
            logger.warning("Prompt missing prompt_id, skipping")
            continue
        variants = generate_all_variants(
            text=prompt_text,
            prompt_id=prompt_id,
            grammar_features=grammar_features,
            grammar_mode=grammar_mode,
            typo_features=typo_features,
            typo_word_p=typo_word_p,
            typo_char_p=typo_char_p,
            seed=seed,
            include_cross_combinations=False,
        )
        for v in variants:
            v["prompt_id"] = prompt_id
            flat.append(v)

    # Summary counts: total variants, grammar-only, typo-only (and optionally cross)
    total = len(flat)
    n_grammar = sum(1 for v in flat if v.get("variant_type") == "grammar")
    n_typo = sum(1 for v in flat if v.get("variant_type") == "typo")
    msg = (
        f"Generated {total} variants across {num_prompts} prompts "
        f"({n_grammar} grammar, {n_typo} typo)"
    )
    logger.info(msg)
    print(msg)

    return flat
