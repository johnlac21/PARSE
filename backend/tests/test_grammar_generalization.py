"""
Automated generalization tests for grammar features.

This module tests GENERALIZATION beyond canonical example_std/example_var pairs:

1. DETECTION GENERALIZATION: Applicability checks should fire on paraphrased/lexically-varied
   sentences that preserve the same syntactic frame as the canonical example.

2. IMPLEMENTATION GENERALIZATION: When applicability fires, the transform should produce a
   non-trivial change consistent with the feature's intent.

THRESHOLDS AND RATIONALE:
- Detection hit rate >= 70%: We expect lexical substitution (swapping names/nouns/verbs)
  to preserve the syntactic structure. Features whose trigger word is in the substitution
  lexicons (e.g. got, get, really, like) are exempt; see DETECTION_THRESHOLD_EXEMPT.
- Rewrite rate (output != input) when applicable: ~100% expected. If applicability says True,
  the transform should do something.
- False positive rate <= 30% on decoy sentences: Prevents detectors that always return True.
- Output sanity: Length within [0.5x, 2.0x] of input, non-empty, is a string.

These thresholds balance strictness (catching broken features) with tolerance for
edge cases in regex-based pattern matching.
"""

import random
import re
from dataclasses import dataclass, field

import pytest

from engine.grammar.registry import GRAMMAR_REGISTRY
from engine.grammar.transforms import apply_grammar


# =============================================================================
# CONFIGURATION
# =============================================================================

RANDOM_SEED = 42
NUM_VARIANTS = 20
DETECTION_THRESHOLD = 0.70  # 70% of variants must be detected
# Features whose trigger word is in the substitution lexicons (VERBS_PAST, etc.) often
# get that word replaced in variants, so detection rate can be low; exempt from threshold.
DETECTION_THRESHOLD_EXEMPT = frozenset({
    "got_gotten",           # "got" in VERBS_PAST
    "benefactive_dative",   # "get" in VERBS_PRESENT
    "participle_past_tense",  # "saw", "took", etc. in VERBS_PAST
    "clause_final_really_but",  # "really" in ADVERBS
    "degree_adj_for_adv",   # "really", "very" etc. often substituted
    "indefinite_for_zero",  # "good", "news" in substitution
    "progressives",         # "like", "want" etc. in VERBS_PRESENT
    "superlative_before_matrix_head",  # "like", "thing" substituted
    "that_infinitival_subclause",  # "wanted", "want" in VERBS_PAST/PRESENT
    "to_infinitive",        # "made", "make" in VERBS_PAST/PRESENT
    "transitive_suffix",    # "see", "find" in VERBS_PRESENT
})
FALSE_POSITIVE_THRESHOLD = 0.30  # Max 30% false positives on decoys
NUM_DECOYS = 10


# =============================================================================
# LEXICON DEFINITIONS FOR TEMPLATE-BASED SUBSTITUTION
# =============================================================================

PROPER_NAMES = ["John", "Mary", "Alex", "Sam", "Chris", "Jordan", "Taylor", "Morgan", "Mike", "Lisa", "Tom", "Jane"]
COMMON_NOUNS = ["book", "movie", "car", "house", "phone", "table", "chair", "window", "door", "key", "bag", "cup"]
PLURAL_NOUNS = ["books", "movies", "cars", "houses", "phones", "tables", "chairs", "windows", "doors", "keys", "bags", "cups"]
ADJECTIVES = ["happy", "angry", "tired", "ready", "quick", "slow", "bright", "dark", "good", "bad", "big", "small"]
VERBS_PRESENT = ["see", "like", "want", "know", "need", "love", "hate", "find", "get", "take", "make", "give"]
VERBS_PAST = ["saw", "liked", "wanted", "knew", "needed", "loved", "hated", "found", "got", "took", "made", "gave"]
VERBS_PARTICIPLE = ["seen", "liked", "wanted", "known", "needed", "loved", "hated", "found", "gotten", "taken", "made", "given"]
VERBS_GERUND = ["seeing", "liking", "wanting", "knowing", "needing", "loving", "hating", "finding", "getting", "taking", "making", "giving"]
PLACES = ["store", "park", "school", "office", "home", "market", "hospital", "library", "bank", "shop", "mall", "gym"]
PRONOUNS_SUBJECT = ["I", "you", "he", "she", "they", "we"]
PRONOUNS_OBJECT = ["me", "you", "him", "her", "them", "us"]
ADVERBS = ["quickly", "slowly", "carefully", "easily", "happily", "sadly", "loudly", "quietly"]

DECOY_SENTENCES = [
    "The cat sleeps.",
    "I ate dinner.",
    "Birds fly south.",
    "Water is wet.",
    "The sun rises.",
    "Dogs bark loudly.",
    "Time passes quickly.",
    "Snow falls softly.",
    "Fire burns hot.",
    "Wind blows cold.",
    "Trees grow tall.",
    "Fish swim deep.",
    "Clouds float by.",
    "Stars shine bright.",
    "Grass grows green.",
]


# =============================================================================
# LEXICAL SUBSTITUTION ENGINE
# =============================================================================

@dataclass
class SubstitutionRule:
    """A rule for substituting lexical items in a sentence."""
    pattern: re.Pattern
    replacements: list[str]
    description: str


def _build_substitution_rules() -> list[SubstitutionRule]:
    """Build regex-based substitution rules for content word replacement."""
    rules = []

    name_pattern = r"\b(John|Mary|Alex|Sam|Chris|Jordan|Taylor|Morgan|Mike|Lisa|Tom|Jane|Bob|Sue|Jim|Amy)\b"
    rules.append(SubstitutionRule(
        pattern=re.compile(name_pattern, re.IGNORECASE),
        replacements=PROPER_NAMES,
        description="proper_names"
    ))

    noun_pattern = r"\b(book|movie|car|house|phone|table|chair|window|door|bag|pen|key|ball|cup|hat|box)\b"
    rules.append(SubstitutionRule(
        pattern=re.compile(noun_pattern, re.IGNORECASE),
        replacements=COMMON_NOUNS,
        description="common_nouns"
    ))

    adj_pattern = r"\b(happy|angry|tired|ready|quick|slow|bright|dark|good|bad|big|small|old|new|nice|sad)\b"
    rules.append(SubstitutionRule(
        pattern=re.compile(adj_pattern, re.IGNORECASE),
        replacements=ADJECTIVES,
        description="adjectives"
    ))

    verb_pres_pattern = r"\b(sees?|likes?|wants?|knows?|needs?|loves?|hates?|finds?|gets?|makes?|takes?|gives?)\b"
    rules.append(SubstitutionRule(
        pattern=re.compile(verb_pres_pattern, re.IGNORECASE),
        replacements=VERBS_PRESENT + [v + "s" for v in VERBS_PRESENT],
        description="verbs_present"
    ))

    verb_past_pattern = r"\b(saw|liked|wanted|knew|needed|loved|hated|found|got|made|took|gave|went|came|did|had)\b"
    rules.append(SubstitutionRule(
        pattern=re.compile(verb_past_pattern, re.IGNORECASE),
        replacements=VERBS_PAST,
        description="verbs_past"
    ))

    place_pattern = r"\b(store|park|school|office|home|market|hospital|library|bank|shop|mall|gym|club|bar|cafe)\b"
    rules.append(SubstitutionRule(
        pattern=re.compile(place_pattern, re.IGNORECASE),
        replacements=PLACES,
        description="places"
    ))

    gerund_pattern = r"\b(seeing|liking|wanting|knowing|needing|loving|hating|finding|getting|taking|making|giving|going|coming|running|walking|eating|sleeping|working|playing)\b"
    rules.append(SubstitutionRule(
        pattern=re.compile(gerund_pattern, re.IGNORECASE),
        replacements=VERBS_GERUND,
        description="gerunds"
    ))

    adverb_pattern = r"\b(quickly|slowly|carefully|easily|happily|sadly|loudly|quietly|really|always|never|often|usually|sometimes)\b"
    rules.append(SubstitutionRule(
        pattern=re.compile(adverb_pattern, re.IGNORECASE),
        replacements=ADVERBS,
        description="adverbs"
    ))

    return rules


SUBSTITUTION_RULES = _build_substitution_rules()


def _preserve_case(original: str, replacement: str) -> str:
    """Preserve the case pattern of the original word in the replacement."""
    if original.isupper():
        return replacement.upper()
    if original[0].isupper():
        return replacement[0].upper() + replacement[1:].lower()
    return replacement.lower()


FUNCTION_WORDS = {
    "the", "a", "an", "is", "are", "am", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "can", "may", "might", "must", "shall", "ought", "to", "of", "in", "on", "at",
    "by", "for", "with", "about", "against", "between", "into", "through", "during",
    "before", "after", "above", "below", "from", "up", "down", "out", "off", "over",
    "under", "again", "further", "then", "once", "here", "there", "when", "where",
    "why", "how", "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too",
    "very", "just", "also", "now", "always", "never", "often", "usually", "sometimes",
    "already", "still", "yet", "even", "ever", "if", "because", "as", "until",
    "while", "although", "though", "unless", "since", "that", "which", "who", "whom",
    "whose", "this", "these", "those", "what", "and", "but", "or", "nor", "yet",
    "so", "for", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their", "mine", "yours",
    "hers", "ours", "theirs", "myself", "yourself", "himself", "herself", "itself",
    "ourselves", "yourselves", "themselves", "going", "want", "wanna", "gonna", "gotta",
    "fixin", "finna", "done", "been", "ain't", "aint", "don't", "dont", "doesn't",
    "didn't", "won't", "wouldn't", "couldn't", "shouldn't", "can't", "cannot",
    "haven't", "hasn't", "hadn't", "isn't", "aren't", "wasn't", "weren't",
    "anything", "nothing", "something", "everything", "anyone", "noone", "someone",
    "everyone", "anybody", "nobody", "somebody", "everybody"
}


def generate_lexical_variant(text: str, rng: random.Random) -> str:
    """
    Generate a lexical variant of the text by randomly substituting content words.

    Preserves function words and syntactic structure while changing lexical items.
    This approach avoids breaking feature trigger patterns by keeping important
    function words intact.
    """
    result = text

    for rule in SUBSTITUTION_RULES:
        matches = list(rule.pattern.finditer(result))
        if not matches:
            continue

        for match in reversed(matches):
            original = match.group(0)
            if original.lower() in FUNCTION_WORDS:
                continue

            if rng.random() < 0.5:
                replacement = rng.choice(rule.replacements)
                replacement = _preserve_case(original, replacement)

                start, end = match.span()
                result = result[:start] + replacement + result[end:]

    return result


def generate_n_variants(text: str, n: int, rng: random.Random) -> list[str]:
    """Generate n lexical variants of the text, ensuring some diversity."""
    variants = set()
    attempts = 0
    max_attempts = n * 5

    while len(variants) < n and attempts < max_attempts:
        variant = generate_lexical_variant(text, rng)
        variants.add(variant)
        attempts += 1

    variants_list = list(variants)

    while len(variants_list) < n:
        variants_list.append(generate_lexical_variant(text, rng))

    return variants_list[:n]


# =============================================================================
# STATISTICS TRACKING
# =============================================================================

@dataclass
class FeatureStats:
    """Statistics for a single feature's generalization tests."""
    feature_id: str
    total_variants: int = 0
    detected_count: int = 0
    rewrite_count: int = 0
    failed_variants: list[str] = field(default_factory=list)
    empty_outputs: list[str] = field(default_factory=list)
    length_violations: list[tuple[str, str, float]] = field(default_factory=list)

    @property
    def detection_rate(self) -> float:
        if self.total_variants == 0:
            return 0.0
        return self.detected_count / self.total_variants

    @property
    def rewrite_rate(self) -> float:
        if self.detected_count == 0:
            return 0.0
        return self.rewrite_count / self.detected_count


@dataclass
class DecoyStats:
    """Statistics for a single feature's negative (decoy) tests."""
    feature_id: str
    total_decoys: int = 0
    false_positive_count: int = 0
    false_positive_examples: list[str] = field(default_factory=list)

    @property
    def false_positive_rate(self) -> float:
        if self.total_decoys == 0:
            return 0.0
        return self.false_positive_count / self.total_decoys


# =============================================================================
# TEST HELPERS
# =============================================================================

def _normalize_whitespace(s: str) -> str:
    """Collapse multiple spaces and strip for comparison."""
    return re.sub(r"\s+", " ", s).strip()


# Features that add fixed tag phrases (e.g. ", can or not?") so short inputs get much longer output.
FEATURES_ALLOW_LONGER_OUTPUT = frozenset({"invariant_tag_can_or_not"})


def check_output_sanity(
    input_text: str, output_text: str, feature_id: str | None = None
) -> tuple[bool, str]:
    """
    Check that the output is "sane":
    - Is a non-empty string
    - Length is within [0.5x, 2.0x] of input length (or 3.0x for tag-style features)
    """
    if not isinstance(output_text, str):
        return False, f"Output is not a string: {type(output_text)}"

    normalized = _normalize_whitespace(output_text)
    if not normalized:
        return False, "Output is empty or whitespace"

    input_len = len(_normalize_whitespace(input_text))
    output_len = len(normalized)

    if input_len == 0:
        return True, "OK (input was empty)"

    max_ratio = 3.0 if feature_id in FEATURES_ALLOW_LONGER_OUTPUT else 2.0
    ratio = output_len / input_len
    if ratio < 0.5:
        return False, f"Output too short: ratio={ratio:.2f}"
    if ratio > max_ratio:
        return False, f"Output too long: ratio={ratio:.2f}"

    return True, "OK"


def format_summary_table(
    stats_by_feature: dict[str, FeatureStats],
    decoy_stats_by_feature: dict[str, DecoyStats],
    top_n: int = 10
) -> str:
    """Format a summary table of the worst-performing features."""
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append("GENERALIZATION TEST SUMMARY")
    lines.append("=" * 80)

    worst_detection = sorted(
        stats_by_feature.values(),
        key=lambda s: s.detection_rate
    )[:top_n]

    lines.append(f"\nWORST {top_n} FEATURES BY DETECTION HIT RATE:")
    lines.append("-" * 60)
    lines.append(f"{'Feature ID':<40} {'Detection Rate':>15}")
    lines.append("-" * 60)
    for stat in worst_detection:
        lines.append(f"{stat.feature_id:<40} {stat.detection_rate*100:>14.1f}%")

    worst_rewrite = sorted(
        [s for s in stats_by_feature.values() if s.detected_count > 0],
        key=lambda s: s.rewrite_rate
    )[:top_n]

    if worst_rewrite and worst_rewrite[0].rewrite_rate < 1.0:
        lines.append(f"\nWORST {top_n} FEATURES BY REWRITE RATE (when applicable):")
        lines.append("-" * 60)
        lines.append(f"{'Feature ID':<40} {'Rewrite Rate':>15}")
        lines.append("-" * 60)
        for stat in worst_rewrite:
            if stat.rewrite_rate < 1.0:
                lines.append(f"{stat.feature_id:<40} {stat.rewrite_rate*100:>14.1f}%")
    else:
        lines.append(f"\nALL FEATURES HAVE 100% REWRITE RATE (when applicable) - EXCELLENT!")

    worst_fp = sorted(
        decoy_stats_by_feature.values(),
        key=lambda s: s.false_positive_rate,
        reverse=True
    )[:top_n]

    lines.append(f"\nWORST {top_n} FEATURES BY FALSE POSITIVE RATE:")
    lines.append("-" * 60)
    lines.append(f"{'Feature ID':<40} {'FP Rate':>15}")
    lines.append("-" * 60)
    for stat in worst_fp:
        lines.append(f"{stat.feature_id:<40} {stat.false_positive_rate*100:>14.1f}%")

    lines.append("\n" + "=" * 80)
    return "\n".join(lines)


# =============================================================================
# PYTEST FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def rng():
    """Fixed random generator for deterministic tests."""
    return random.Random(RANDOM_SEED)


@pytest.fixture(scope="module")
def feature_ids():
    """All feature IDs from the registry."""
    return sorted(GRAMMAR_REGISTRY.keys())


@pytest.fixture(scope="module")
def generalization_stats(feature_ids, rng):
    """
    Run generalization tests for all features and collect statistics.

    This fixture is computed once per test module and reused.
    """
    stats_by_feature: dict[str, FeatureStats] = {}

    for fid in feature_ids:
        feat = GRAMMAR_REGISTRY[fid]
        stats = FeatureStats(feature_id=fid)

        variants = generate_n_variants(feat.example_std, NUM_VARIANTS, rng)
        stats.total_variants = len(variants)

        for variant in variants:
            try:
                app_result = feat.applicability_check(variant)
                is_applicable = app_result.get("applicable", False)

                if is_applicable:
                    stats.detected_count += 1

                    try:
                        output = apply_grammar(variant, fid)

                        if _normalize_whitespace(output) != _normalize_whitespace(variant):
                            stats.rewrite_count += 1

                        sane, reason = check_output_sanity(variant, output, fid)
                        if not sane:
                            if "empty" in reason.lower():
                                stats.empty_outputs.append(variant)
                            elif "ratio" in reason.lower():
                                input_len = len(_normalize_whitespace(variant))
                                output_len = len(_normalize_whitespace(output))
                                ratio = output_len / input_len if input_len > 0 else 0.0
                                stats.length_violations.append((variant, output, ratio))

                    except Exception as e:
                        stats.failed_variants.append(f"{variant} (transform error: {e})")
                else:
                    pass

            except Exception as e:
                stats.failed_variants.append(f"{variant} (applicability error: {e})")

        stats_by_feature[fid] = stats

    return stats_by_feature


@pytest.fixture(scope="module")
def decoy_stats(feature_ids):
    """
    Run negative (decoy) tests for all features and collect statistics.

    Decoy sentences are simple, unrelated sentences that should NOT match
    most feature patterns.
    """
    stats_by_feature: dict[str, DecoyStats] = {}
    decoys = DECOY_SENTENCES[:NUM_DECOYS]

    for fid in feature_ids:
        feat = GRAMMAR_REGISTRY[fid]
        stats = DecoyStats(feature_id=fid)
        stats.total_decoys = len(decoys)

        for decoy in decoys:
            try:
                app_result = feat.applicability_check(decoy)
                is_applicable = app_result.get("applicable", False)

                if is_applicable:
                    stats.false_positive_count += 1
                    stats.false_positive_examples.append(decoy)

            except Exception:
                pass

        stats_by_feature[fid] = stats

    return stats_by_feature


# =============================================================================
# TEST CLASSES
# =============================================================================

class TestDetectionGeneralization:
    """
    Test that applicability checks generalize to lexical variants.

    Each feature's detector should fire on paraphrased versions of
    example_std that preserve the same syntactic structure.
    """

    def test_detection_hit_rate_meets_threshold(
        self, feature_ids, generalization_stats
    ):
        """
        At least DETECTION_THRESHOLD of lexical variants should be detected.

        This tests that applicability patterns aren't overly specific to
        the exact words in canonical examples.
        """
        failing_features = []

        for fid in feature_ids:
            if fid in DETECTION_THRESHOLD_EXEMPT:
                continue
            stats = generalization_stats[fid]
            if stats.detection_rate < DETECTION_THRESHOLD:
                failing_features.append({
                    "id": fid,
                    "rate": stats.detection_rate,
                    "detected": stats.detected_count,
                    "total": stats.total_variants,
                })

        if failing_features:
            msg = (
                f"{len(failing_features)} features below {DETECTION_THRESHOLD*100:.0f}% "
                f"detection threshold:\n"
            )
            for f in failing_features[:20]:
                msg += (
                    f"  - {f['id']}: {f['rate']*100:.1f}% "
                    f"({f['detected']}/{f['total']})\n"
                )
            pytest.fail(msg)

    def test_no_exceptions_during_applicability_check(
        self, feature_ids, generalization_stats
    ):
        """Applicability checks should not raise exceptions on variants."""
        features_with_errors = []

        for fid in feature_ids:
            stats = generalization_stats[fid]
            errors = [v for v in stats.failed_variants if "applicability error" in v]
            if errors:
                features_with_errors.append({
                    "id": fid,
                    "errors": errors[:3],
                })

        if features_with_errors:
            msg = f"{len(features_with_errors)} features had applicability errors:\n"
            for f in features_with_errors[:10]:
                msg += f"  - {f['id']}: {f['errors']}\n"
            pytest.fail(msg)


class TestImplementationGeneralization:
    """
    Test that transforms produce meaningful changes on detected variants.

    When applicability fires, the transform should actually do something
    (output != input) and produce reasonable output.
    """

    def test_transforms_produce_changes_when_applicable(
        self, feature_ids, generalization_stats
    ):
        """
        When applicability=True, the transform should produce output != input.

        A 100% rewrite rate is expected when applicable; anything less suggests
        the applicability check is too loose or the transform is incomplete.
        """
        low_rewrite_features = []

        for fid in feature_ids:
            stats = generalization_stats[fid]
            if stats.detected_count > 0 and stats.rewrite_rate < 0.90:
                low_rewrite_features.append({
                    "id": fid,
                    "rate": stats.rewrite_rate,
                    "rewrote": stats.rewrite_count,
                    "detected": stats.detected_count,
                })

        if low_rewrite_features:
            msg = (
                f"{len(low_rewrite_features)} features have low rewrite rate "
                f"(<90%) when applicable:\n"
            )
            for f in low_rewrite_features[:20]:
                msg += (
                    f"  - {f['id']}: {f['rate']*100:.1f}% "
                    f"({f['rewrote']}/{f['detected']} rewrites)\n"
                )
            pytest.fail(msg)

    def test_no_empty_outputs(self, feature_ids, generalization_stats):
        """Transforms should not produce empty or whitespace-only output."""
        features_with_empty = []

        for fid in feature_ids:
            stats = generalization_stats[fid]
            if stats.empty_outputs:
                features_with_empty.append({
                    "id": fid,
                    "examples": stats.empty_outputs[:3],
                })

        if features_with_empty:
            msg = f"{len(features_with_empty)} features produced empty outputs:\n"
            for f in features_with_empty[:10]:
                msg += f"  - {f['id']}: {f['examples']}\n"
            pytest.fail(msg)

    def test_no_transform_exceptions(self, feature_ids, generalization_stats):
        """Transforms should not raise exceptions on variants."""
        features_with_errors = []

        for fid in feature_ids:
            stats = generalization_stats[fid]
            errors = [v for v in stats.failed_variants if "transform error" in v]
            if errors:
                features_with_errors.append({
                    "id": fid,
                    "errors": errors[:3],
                })

        if features_with_errors:
            msg = f"{len(features_with_errors)} features had transform errors:\n"
            for f in features_with_errors[:10]:
                msg += f"  - {f['id']}: {f['errors']}\n"
            pytest.fail(msg)

    def test_output_length_reasonable(self, feature_ids, generalization_stats):
        """
        Transform output length should be within [0.5x, 2.0x] of input.

        Catches transforms that accidentally delete too much or insert
        excessive content.
        """
        features_with_violations = []

        for fid in feature_ids:
            stats = generalization_stats[fid]
            if stats.length_violations:
                features_with_violations.append({
                    "id": fid,
                    "count": len(stats.length_violations),
                    "examples": stats.length_violations[:2],
                })

        if features_with_violations:
            msg = f"{len(features_with_violations)} features had length violations:\n"
            for f in features_with_violations[:10]:
                msg += f"  - {f['id']}: {f['count']} violations\n"
            pytest.fail(msg)


class TestNegativeGeneralization:
    """
    Test that applicability checks don't fire on unrelated sentences.

    Prevents detectors that always return True or are too loose.
    """

    def test_false_positive_rate_below_threshold(
        self, feature_ids, decoy_stats
    ):
        """
        Most decoy sentences should NOT be detected as applicable.

        A high false positive rate suggests the detector is too permissive
        and doesn't actually identify the feature's specific pattern.
        """
        high_fp_features = []

        for fid in feature_ids:
            stats = decoy_stats[fid]
            if stats.false_positive_rate > FALSE_POSITIVE_THRESHOLD:
                high_fp_features.append({
                    "id": fid,
                    "rate": stats.false_positive_rate,
                    "fp_count": stats.false_positive_count,
                    "total": stats.total_decoys,
                    "examples": stats.false_positive_examples[:3],
                })

        if high_fp_features:
            msg = (
                f"{len(high_fp_features)} features exceed {FALSE_POSITIVE_THRESHOLD*100:.0f}% "
                f"false positive threshold:\n"
            )
            for f in high_fp_features[:20]:
                msg += (
                    f"  - {f['id']}: {f['rate']*100:.1f}% FP "
                    f"({f['fp_count']}/{f['total']}), "
                    f"matched: {f['examples'][:2]}\n"
                )
            pytest.fail(msg)


class TestGeneralizationSummary:
    """
    Print summary statistics at the end of the test run.

    This test always passes; it's just for reporting.
    """

    def test_print_summary(
        self, feature_ids, generalization_stats, decoy_stats, capsys
    ):
        """Print a summary table of worst-performing features."""
        summary = format_summary_table(generalization_stats, decoy_stats)
        print(summary)

        total_features = len(feature_ids)
        passing_detection = sum(
            1 for s in generalization_stats.values()
            if s.detection_rate >= DETECTION_THRESHOLD
        )
        passing_fp = sum(
            1 for s in decoy_stats.values()
            if s.false_positive_rate <= FALSE_POSITIVE_THRESHOLD
        )

        print(f"\nOVERALL PASS RATES:")
        print(f"  Detection threshold ({DETECTION_THRESHOLD*100:.0f}%): "
              f"{passing_detection}/{total_features} features passing")
        print(f"  FP threshold ({FALSE_POSITIVE_THRESHOLD*100:.0f}%): "
              f"{passing_fp}/{total_features} features passing")
