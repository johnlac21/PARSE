"""
Pytest tests for typo transforms.

Run from backend directory: cd backend && PYTHONPATH=. pytest tests/test_typo_transforms.py -v
"""

from __future__ import annotations

import pytest

from engine.typos.registry import TYPO_REGISTRY
from engine.typos.transforms import (
    typo_char_delete,
    typo_char_double,
    typo_char_swap,
    typo_keyboard_prox,
    typo_typoglycemia,
    typo_whitespace,
)

TYPOS = [
    typo_keyboard_prox,
    typo_char_swap,
    typo_char_double,
    typo_char_delete,
    typo_whitespace,
    typo_typoglycemia,
]

SEED = 123
SAMPLE_TEXT = "recommend a film for the evening"


# --- Determinism (fixed seed → same output) ---


@pytest.mark.parametrize("typo_fn", TYPOS)
def test_determinism_fixed_seed(typo_fn):
    """Each function with a fixed seed produces the same output every time."""
    out1 = typo_fn(SAMPLE_TEXT, word_p=0.5, char_p=0.5, seed=SEED)
    out2 = typo_fn(SAMPLE_TEXT, word_p=0.5, char_p=0.5, seed=SEED)
    assert out1 == out2


# --- word_p=0.0 returns original text unchanged ---


@pytest.mark.parametrize("typo_fn", TYPOS)
def test_word_p_zero_returns_unchanged(typo_fn):
    """With word_p=0.0 the text is returned unchanged."""
    assert typo_fn(SAMPLE_TEXT, word_p=0.0, char_p=0.6, seed=SEED) == SAMPLE_TEXT


# --- word_p=1.0 modifies words ---


@pytest.mark.parametrize("typo_fn", TYPOS)
def test_word_p_one_modifies(typo_fn):
    """With word_p=1.0 most or all words are modified (output differs from input for our sample)."""
    out = typo_fn(SAMPLE_TEXT, word_p=1.0, char_p=0.6, seed=SEED)
    assert isinstance(out, str)
    # With word_p=1.0 and fixed seed, we expect the sample text to be modified
    # (at least one word or space change). Some seeds might leave output equal;
    # we use a seed that produces a change for our sample.
    assert out != SAMPLE_TEXT, f"{typo_fn.__name__} with word_p=1.0 should modify the text"


# --- Empty string returns empty string ---


@pytest.mark.parametrize("typo_fn", TYPOS)
def test_empty_string_returns_empty(typo_fn):
    """Empty string input returns empty string."""
    assert typo_fn("", word_p=0.15, char_p=0.6, seed=SEED) == ""


# --- Registry ---


def test_registry_has_six_features():
    """All 6 typo functions are registered."""
    expected_ids = [
        "typo_keyboard_prox",
        "typo_char_swap",
        "typo_char_double",
        "typo_char_delete",
        "typo_whitespace",
        "typo_typoglycemia",
    ]
    for fid in expected_ids:
        assert fid in TYPO_REGISTRY
    assert len(TYPO_REGISTRY) == 6


def test_registry_feature_has_required_fields():
    """Each TypoFeature has id, name, description, example, transform, default_word_p, default_char_p."""
    for fid, feat in TYPO_REGISTRY.items():
        assert feat.id == fid
        assert feat.name
        assert feat.description
        assert feat.example
        assert callable(feat.transform)
        assert 0 <= feat.default_word_p <= 1
        assert 0 <= feat.default_char_p <= 1
