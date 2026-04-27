"""
Tests for all Ziems grammar features (paper 189).

Verifies that:
- All features from shared/grammar_features.json are in the registry.
- Every feature has a real transform (no no-ops).
- For each feature, apply_grammar(example_std, feature_id) runs without error.
- For every feature, apply_grammar(example_std, feature_id) equals (after normalizing whitespace)
  the documented example_var.
- Applicability check runs and returns a valid dict for every feature.
"""

import re

import pytest

from engine.grammar.registry import GRAMMAR_REGISTRY, load_features_from_json
from engine.grammar.transforms import apply_grammar


def _normalize_whitespace(s: str) -> str:
    """Collapse multiple spaces and strip for comparison."""
    return re.sub(r"\s+", " ", s).strip()


# Ziems Multi-Value paper (2212.pdf) implements 189 features
GRAMMAR_FEATURE_COUNT = 189

class TestGrammarFeatureCount:
    """All Ziems grammar features are registered and have real transforms."""

    def test_registry_has_paper_feature_count(self):
        assert len(GRAMMAR_REGISTRY) == GRAMMAR_FEATURE_COUNT, (
            f"Expected {GRAMMAR_FEATURE_COUNT} grammar features, got {len(GRAMMAR_REGISTRY)}"
        )

    def test_no_feature_uses_noop_transform(self):
        noop_ids = [
            fid
            for fid, f in GRAMMAR_REGISTRY.items()
            if getattr(f.transform, "__name__", "") == "_transform_noop"
        ]
        assert not noop_ids, (
            f"Features still using no-op transform: {noop_ids}"
        )

    def test_every_feature_has_transform_and_applicability(self):
        missing = [
            fid
            for fid, f in GRAMMAR_REGISTRY.items()
            if f.transform is None or f.applicability_check is None
        ]
        assert not missing, (
            f"Features missing transform or applicability_check: {missing}"
        )


class TestGrammarTransformsApply:
    """Each feature's transform runs without error and matches example_var."""

    @pytest.fixture(scope="class")
    def feature_ids(self):
        return sorted(GRAMMAR_REGISTRY.keys())

    def test_apply_grammar_returns_string_for_every_feature(self, feature_ids):
        for fid in feature_ids:
            feat = GRAMMAR_REGISTRY[fid]
            result = apply_grammar(feat.example_std, fid)
            assert isinstance(result, str), (
                f"{fid}: apply_grammar should return str, got {type(result)}"
            )

    def test_apply_grammar_matches_example_var_for_every_feature(self, feature_ids):
        """For each feature, apply_grammar(example_std) must equal example_var (after normalizing whitespace)."""
        mismatches = []
        for fid in feature_ids:
            feat = GRAMMAR_REGISTRY[fid]
            result = apply_grammar(feat.example_std, fid)
            expected = feat.example_var
            norm_result = _normalize_whitespace(result)
            norm_expected = _normalize_whitespace(expected)
            if norm_result != norm_expected:
                mismatches.append({
                    "id": fid,
                    "example_std": feat.example_std,
                    "expected": expected,
                    "got": result,
                })
        match_count = len(feature_ids) - len(mismatches)
        assert match_count == GRAMMAR_FEATURE_COUNT, (
            f"Expected all {GRAMMAR_FEATURE_COUNT} features to match example_var; {match_count}/{GRAMMAR_FEATURE_COUNT} matched. "
            f"Mismatches (first 20): "
            + "; ".join(
                f"{m['id']}: got {m['got']!r}"
                for m in mismatches[:20]
            )
        )


class TestGrammarApplicability:
    """Applicability check runs without error for every feature."""

    def test_applicability_returns_dict_for_every_feature(self):
        for fid, feat in GRAMMAR_REGISTRY.items():
            check = feat.applicability_check
            assert check is not None, f"{fid}: applicability_check is None"
            result = check(feat.example_std)
            assert isinstance(result, dict), (
                f"{fid}: applicability_check should return dict, got {type(result)}"
            )
            assert "applicable" in result, f"{fid}: result missing 'applicable'"
            assert "reason" in result, f"{fid}: result missing 'reason'"

    def test_applicability_detects_canonical_example_for_every_feature(self):
        """For each feature, example_std is detected as applicable (applicable=True)."""
        not_applicable = []
        for fid, feat in GRAMMAR_REGISTRY.items():
            result = feat.applicability_check(feat.example_std)
            if not result.get("applicable", False):
                not_applicable.append({
                    "id": fid,
                    "reason": result.get("reason", "unknown"),
                })
        assert not not_applicable, (
            f"Expected every feature to report applicable=True for its own example_std. "
            f"Features where example_std was not detected as applicable ({len(not_applicable)}): "
            + "; ".join(f"{m['id']}: {m['reason'][:50]!r}" for m in not_applicable[:20])
        )
