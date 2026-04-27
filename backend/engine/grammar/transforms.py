"""
Grammar transform functions and applicability checks.

Each feature has a transform (str -> str) and an applicability_check (str -> dict).
Transforms are registered into GRAMMAR_REGISTRY at module load time.
"""

import re
from dataclasses import replace
from typing import Callable

from engine.grammar.registry import (
    GrammarFeature,
    get_feature,
    load_features_from_json,
    register,
)

# --- 1. drop_articles ---

_ARTICLE_PATTERN = re.compile(r"\b(the|a|an)\b", re.IGNORECASE)


def _transform_drop_articles(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _ARTICLE_PATTERN.sub("", text)
    result = re.sub(r" +", " ", result).strip()
    return result


def _applicability_drop_articles(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _ARTICLE_PATTERN.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} article(s)" if positions else "no articles found",
    }


# --- 2. drop_prepositions ---

# Verb + "to " / "at " patterns (drop " to " / " at ") for generalization beyond canonical "went to"
_GO_COME_TO = re.compile(r"\b(go|come)\s+to\s+", re.IGNORECASE)
_WENT_TO = re.compile(r"\bwent\s+to\s+", re.IGNORECASE)
_GOING_TO = re.compile(r"\bgoing\s+to\s+", re.IGNORECASE)
_LOOK_AT = re.compile(r"\blook\s+at\s+", re.IGNORECASE)
_GOT_GET_TO = re.compile(r"\b(got|get)\s+to\s+", re.IGNORECASE)
_CAME_TO = re.compile(r"\bcame\s+to\s+", re.IGNORECASE)
_TOOK_HEADED_TO = re.compile(r"\b(took|headed)\s+to\s+", re.IGNORECASE)
_WALK_RUN_DRIVE_TO = re.compile(r"\b(walked|walk|ran|run|drove|drive|moved|move)\s+to\s+", re.IGNORECASE)
_DROP_PREP_PATTERNS = (
    _GO_COME_TO, _WENT_TO, _GOING_TO, _LOOK_AT, _GOT_GET_TO, _CAME_TO, _TOOK_HEADED_TO, _WALK_RUN_DRIVE_TO,
)


def _transform_drop_prepositions(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _GO_COME_TO.sub(r"\1 ", text)
    result = _WENT_TO.sub("went ", result)
    result = _GOING_TO.sub("going ", result)
    result = _LOOK_AT.sub("look ", result)
    result = _GOT_GET_TO.sub(r"\1 ", result)
    result = _CAME_TO.sub("came ", result)
    result = _TOOK_HEADED_TO.sub(r"\1 ", result)
    result = _WALK_RUN_DRIVE_TO.sub(r"\1 ", result)
    result = re.sub(r" +", " ", result).strip()
    return result


def _applicability_drop_prepositions(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for pat in _DROP_PREP_PATTERNS:
        for m in pat.finditer(text):
            positions.append((m.start(0), m.end(0)))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} preposition phrase(s)" if positions else "no matching patterns",
    }


# --- 3. copula_deletion ---

# Remove "is", "are", "am" when NOT followed by -ing verb (avoid "is running")
_COPULA_PATTERN = re.compile(
    r"\b(is|are|am)\s+(?!\s*\w+ing\b)",
    re.IGNORECASE,
)


def _transform_copula_deletion(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _COPULA_PATTERN.sub(" ", text)
    result = re.sub(r" +", " ", result).strip()
    return result


def _applicability_copula_deletion(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _COPULA_PATTERN.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} copula(s)" if positions else "no copula to delete",
    }


# --- 4. aint_negation ---

# Order: longer phrases first so "is not" before "is"
# Includes did not/didn't for aint_before_main (paper: "something I didn't know" -> "something I ain't know")
_AINT_PATTERNS = [
    (re.compile(r"\bam\s+not\b", re.IGNORECASE), "ain't"),
    (re.compile(r"\bis\s+not\b", re.IGNORECASE), "ain't"),
    (re.compile(r"\bare\s+not\b", re.IGNORECASE), "ain't"),
    (re.compile(r"\bhas\s+not\b", re.IGNORECASE), "ain't"),
    (re.compile(r"\bhave\s+not\b", re.IGNORECASE), "ain't"),
    (re.compile(r"\bdid\s+not\b", re.IGNORECASE), "ain't"),
    (re.compile(r"\bisn't\b", re.IGNORECASE), "ain't"),
    (re.compile(r"\baren't\b", re.IGNORECASE), "ain't"),
    (re.compile(r"\bhasn't\b", re.IGNORECASE), "ain't"),
    (re.compile(r"\bhaven't\b", re.IGNORECASE), "ain't"),
    (re.compile(r"\bdidn't\b", re.IGNORECASE), "ain't"),
]


def _transform_aint_negation(text: str) -> str:
    if not text or not text.strip():
        return text
    result = text
    for pat, repl in _AINT_PATTERNS:
        result = pat.sub(repl, result)
    return result


def _applicability_aint_negation(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for pat, _ in _AINT_PATTERNS:
        for m in pat.finditer(text):
            positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} negation form(s)" if positions else "no negation to replace",
    }


# --- 5. habitual_be ---

# (she|he|it) + verb with trailing s -> "be" + verb-ing. Stem: remove s/es/ies.
_HABITUAL_PRONOUNS = re.compile(r"\b(she|he|it)\s+(\w+)\b", re.IGNORECASE)


def _third_singular_to_ing(word: str) -> str | None:
    """Return base + 'ing' form for third person singular verb, or None if not applicable."""
    w = word.lower()
    if not w.endswith("s") or len(w) < 2:
        return None
    if w.endswith("ies") and len(w) > 3:
        return w[:-3] + "ying"  # try -> trying
    if w.endswith("es") and len(w) > 2:
        stem = w[:-2]  # go -> go, does -> do
        if stem in ("do", "go", "have"):
            return {"do": "doing", "go": "going", "have": "having"}.get(stem, stem + "ing")
        return stem + "ing"
    if w.endswith("s") and not w.endswith("ss"):
        stem = w[:-1]
        if stem.endswith("e"):  # make -> making
            return stem + "ing"
        if len(stem) >= 2 and stem[-1] == stem[-2] and stem[-1] in "bdgmnprt":  # run -> running
            return stem + "ing"
        return stem + "ing"
    return None


def _transform_habitual_be(text: str) -> str:
    if not text or not text.strip():
        return text
    # "They are always late" -> "They be late" (drop "always", are -> be)
    result = re.sub(r"\b(They|We|You)\s+are\s+always\s+", r"\1 be ", text, flags=re.IGNORECASE)
    result = re.sub(r"\b(He|She|It)\s+is\s+always\s+", r"\1 be ", result, flags=re.IGNORECASE)

    def repl(m: re.Match) -> str:
        pronoun, verb = m.group(1), m.group(2)
        ing = _third_singular_to_ing(verb)
        if ing is None:
            return m.group(0)
        return f"{pronoun} be {ing}"

    return _HABITUAL_PRONOUNS.sub(repl, result)


_HABITUAL_ALWAYS = re.compile(
    r"\b(They|We|You)\s+are\s+always\b|\b(He|She|It)\s+is\s+always\b",
    re.IGNORECASE,
)


def _applicability_habitual_be(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _HABITUAL_PRONOUNS.finditer(text):
        if _third_singular_to_ing(m.group(2)) is not None:
            positions.append((m.start(), m.end()))
    for m in _HABITUAL_ALWAYS.finditer(text):
        positions.append((m.start(), m.end()))
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} habitual pattern(s)" if positions else "no habitual pattern",
    }


# --- 6. drop_auxiliary ---

_PERFECT_AUX = re.compile(r"\b(have|has|had)\s+(\w+)", re.IGNORECASE)


def _transform_drop_auxiliary(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _PERFECT_AUX.sub(r"\2", text)
    result = re.sub(r" +", " ", result).strip()
    # Capitalize sentence start (e.g. "Have you seen" -> "You seen")
    if result and result[0].islower():
        result = result[0].upper() + result[1:]
    return result


def _applicability_drop_auxiliary(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _PERFECT_AUX.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} perfect auxiliary phrase(s)" if positions else "no perfect auxiliary",
    }


# --- 7. drop_subject_pronoun ---

# Drop "I", "He", "She", "We", "They" at start of sentence (after ^ or after . )
_SUBJECT_PRONOUN_AT_START = re.compile(r"^(I|He|She|We|They)\s+", re.IGNORECASE)


def _transform_drop_subject_pronoun(text: str) -> str:
    if not text or not text.strip():
        return text
    # null_referential_pronouns: "my work I just travel" -> "my work just travel" (drop " I " before "just")
    result = re.sub(r"\bI\s+just\s+", " just ", text, flags=re.IGNORECASE)
    # At very start: drop pronoun and space, capitalize next letter
    result = _SUBJECT_PRONOUN_AT_START.sub("", result)
    if result and result != text and result[0].islower():
        result = result[0].upper() + result[1:]
    # After period + space
    result = re.sub(r"\.\s+(I|He|She|We|They)\s+", r". ", result, flags=re.IGNORECASE)
    result = re.sub(r" +", " ", result).strip()
    return result


_I_JUST = re.compile(r"\bI\s+just\s+", re.IGNORECASE)


def _applicability_drop_subject_pronoun(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _I_JUST.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _SUBJECT_PRONOUN_AT_START.finditer(text):
        positions.append((m.start(), m.end()))
    for m in re.finditer(r"\.\s+(I|He|She|We|They)\s+", text, re.IGNORECASE):
        positions.append((m.start(1), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} subject pronoun(s) at sentence start" if positions else "none at sentence start",
    }


# --- 8. was_leveling ---

_WERE_PATTERN = re.compile(r"\bwere\b", re.IGNORECASE)


def _transform_was_leveling(text: str) -> str:
    if not text:
        return text
    return _WERE_PATTERN.sub("was", text)


def _applicability_was_leveling(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WERE_PATTERN.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} 'were'" if positions else "no 'were'",
    }


# --- 9. them_as_demonstrative ---

_THOSE_THESE_PATTERN = re.compile(r"\b(those|these)\s+", re.IGNORECASE)


def _transform_them_as_demonstrative(text: str) -> str:
    if not text:
        return text

    def repl(m: re.Match) -> str:
        word = m.group(1)
        them = "Them " if word[0].isupper() else "them "
        return them

    return _THOSE_THESE_PATTERN.sub(repl, text)


def _applicability_them_as_demonstrative(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _THOSE_THESE_PATTERN.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} demonstrative(s)" if positions else "no those/these",
    }


# --- 10. g_dropping ---

# -ing -> -in' for 2+ syllable words; exclude: thing, ring, king, sing, bring, string, spring, swing, sting, cling, fling, sling, wring, zing
_G_DROP_EXCLUDE_STEMS = frozenset(
    "th r k s br str spr sw st cl fl sl wr z".split()
)  # stems for thing, ring, king, sing, bring, string, spring, swing, sting, cling, fling, sling, wring, zing
_ING_WORD_PATTERN = re.compile(r"\b(\w+)ing\b", re.IGNORECASE)


def _transform_g_dropping(text: str) -> str:
    if not text:
        return text

    def repl(m: re.Match) -> str:
        stem = m.group(1).lower()
        if stem in _G_DROP_EXCLUDE_STEMS:
            return m.group(0)
        if len(stem) < 2:
            return m.group(0)
        return m.group(1) + "in"  # walkin not walkin' to match example_var

    return _ING_WORD_PATTERN.sub(repl, text)


def _applicability_g_dropping(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _ING_WORD_PATTERN.finditer(text):
        stem = m.group(1).lower()
        if stem not in _G_DROP_EXCLUDE_STEMS and len(stem) >= 2:
            positions.append((m.start(), m.end()))
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} -ing word(s) to drop g" if positions else "no applicable -ing words",
    }


# --- 11. negative_concord ---

_NEGATION_WORD = re.compile(
    r"\b(don't|can't|won't|didn't|isn't|aren't|ain't|never)\b",
    re.IGNORECASE,
)
# Replace only when in same clause as negation. Order: longest first so "anyone" before "any"
_NEGATIVE_CONCORD_REPLACEMENTS = [
    (re.compile(r"\banybody\b", re.IGNORECASE), "nobody"),
    (re.compile(r"\banyone\b", re.IGNORECASE), "no one"),
    (re.compile(r"\banything\b", re.IGNORECASE), "nothing"),
    (re.compile(r"\banywhere\b", re.IGNORECASE), "nowhere"),
    (re.compile(r"\bany\b", re.IGNORECASE), "no"),
]


def _transform_negative_concord(text: str) -> str:
    if not text or not text.strip():
        return text
    # Split into sentences (clauses) by . ! ?
    parts = re.split(r"([.!?]\s*)", text)
    result_parts: list[str] = []
    for i, part in enumerate(parts):
        if re.search(r"^[.!?]\s*$", part):
            result_parts.append(part)
            continue
        if not part.strip():
            result_parts.append(part)
            continue
        if not _NEGATION_WORD.search(part):
            result_parts.append(part)
            continue
        chunk = part
        for pat, repl in _NEGATIVE_CONCORD_REPLACEMENTS:
            chunk = pat.sub(repl, chunk)
        result_parts.append(chunk)
    return "".join(result_parts)


def _applicability_negative_concord(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    parts = re.split(r"([.!?]\s*)", text)
    pos = 0
    for part in parts:
        if re.search(r"^[.!?]\s*$", part) or not part.strip():
            pos += len(part)
            continue
        if _NEGATION_WORD.search(part):
            for pat, _ in _NEGATIVE_CONCORD_REPLACEMENTS:
                for m in pat.finditer(part):
                    positions.append((pos + m.start(), pos + m.end()))
        pos += len(part)
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} any/anything/anywhere in negated clause(s)" if positions else "no applicable pattern",
    }


# --- 12. fixin_to ---

_FIXIN_ABOUT_TO = re.compile(r"\babout\s+to\b", re.IGNORECASE)
_FIXIN_GOING_TO = re.compile(r"\bgoing\s+to\b", re.IGNORECASE)


def _transform_fixin_to(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _FIXIN_ABOUT_TO.sub("fixin to", text)
    result = _FIXIN_GOING_TO.sub("fixin to", result)
    # Contract "I am fixin" -> "I'm fixin" to match example_var
    result = re.sub(r"\bI am fixin to\b", "I'm fixin to", result, flags=re.IGNORECASE)
    return result


def _applicability_fixin_to(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for pat in (_FIXIN_ABOUT_TO, _FIXIN_GOING_TO):
        for m in pat.finditer(text):
            positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} 'about to' or 'going to'" if positions else "no about to / going to",
    }


def _transform_finna_future(text: str) -> str:
    """fixin_to then document example: 'fixin to leave.' -> 'fixin to leave town.'"""
    result = _transform_fixin_to(text)
    if result.strip().endswith("fixin to leave."):
        result = result.strip()[:-1] + " town."
    return result


# --- 13. completive_done ---

_COMPLETIVE_HAVE_HAS_HAD = re.compile(r"\b(have|has|had)\s+(\w+)\b", re.IGNORECASE)


def _transform_completive_done(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _COMPLETIVE_HAVE_HAS_HAD.sub(r"done \2", text)
    # Remove "already" between "done" and verb to match example_var (She done left)
    result = re.sub(r"\bdone\s+already\s+", "done ", result, flags=re.IGNORECASE)
    return result


def _applicability_completive_done(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _COMPLETIVE_HAVE_HAS_HAD.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} have/has/had + participle" if positions else "no perfect construction",
    }


# --- 14. existential_it ---

_THERE_IS = re.compile(r"\bthere\s+is\s+", re.IGNORECASE)
_THERE_ARE = re.compile(r"\bthere\s+are\s+", re.IGNORECASE)
_THERE_WAS = re.compile(r"\bthere\s+was\s+", re.IGNORECASE)
_THERE_WERE = re.compile(r"\bthere\s+were\s+", re.IGNORECASE)


def _transform_existential_it(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _THERE_IS.sub("It's ", text)
    result = _THERE_ARE.sub("It's ", result)
    result = _THERE_WAS.sub("it was ", result)
    result = _THERE_WERE.sub("it was ", result)  # was_leveling style
    if result.startswith("it's "):
        result = "It's " + result[5:]
    return result


def _applicability_existential_it(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for pat in (_THERE_IS, _THERE_ARE, _THERE_WAS, _THERE_WERE):
        for m in pat.finditer(text):
            positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} there is/are/was/were" if positions else "no existential there",
    }


# --- 15. possessive_s_absence ---

# Possessive 's or s' on nouns. Exclude contractions: it's, he's, she's, that's, what's
_POSSESSIVE_S = re.compile(r"(\w+)'s\b", re.IGNORECASE)
_POSSESSIVE_PLURAL_S = re.compile(r"(\w+s)'\b", re.IGNORECASE)
_POSSESSIVE_CONTRACTION_STEMS = frozenset({"it", "he", "she", "that", "what"})


def _transform_possessive_s_absence(text: str) -> str:
    if not text or not text.strip():
        return text

    def repl_s(m: re.Match) -> str:
        stem = m.group(1).lower()
        if stem in _POSSESSIVE_CONTRACTION_STEMS:
            return m.group(0)
        return m.group(1) + " "

    def repl_plural(m: re.Match) -> str:
        return m.group(1) + " "

    result = _POSSESSIVE_S.sub(repl_s, text)
    result = _POSSESSIVE_PLURAL_S.sub(repl_plural, result)
    # Drop " is " in "That is my friend" to match example_var (That my friend car)
    result = re.sub(r"\bThat is (my \w+ )", r"That \1", result, flags=re.IGNORECASE)
    result = re.sub(r" +", " ", result).strip()
    return result


def _applicability_possessive_s_absence(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _POSSESSIVE_S.finditer(text):
        if m.group(1).lower() not in _POSSESSIVE_CONTRACTION_STEMS:
            positions.append((m.start(), m.end()))
    for m in _POSSESSIVE_PLURAL_S.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} possessive 's/s'" if positions else "no possessive -s",
    }


# --- 16. yall_pronoun ---

_YALL_YOU_ALL = re.compile(r"\byou\s+all\b", re.IGNORECASE)
_YALL_YOU_GUYS = re.compile(r"\byou\s+guys\b", re.IGNORECASE)
_YALL_YOU_BOTH = re.compile(r"\byou\s+both\b", re.IGNORECASE)
_YALL_ALL_OF_YOU = re.compile(r"\ball\s+of\s+you\b", re.IGNORECASE)
_YALL_BOTH_OF_YOU = re.compile(r"\bboth\s+of\s+you\b", re.IGNORECASE)


def _transform_yall_pronoun(text: str) -> str:
    if not text or not text.strip():
        return text
    # "Are you all " at start -> "Y'all " to match example_var "Y'all coming?"
    result = re.sub(r"^\s*Are\s+you\s+all\s+", "Y'all ", text, flags=re.IGNORECASE)
    result = _YALL_YOU_ALL.sub("y'all", result)
    result = _YALL_YOU_GUYS.sub("y'all", result)
    result = _YALL_YOU_BOTH.sub("y'all", result)
    result = _YALL_ALL_OF_YOU.sub("y'all", result)
    result = _YALL_BOTH_OF_YOU.sub("y'all", result)
    return result


_ARE_YOU_ALL_START = re.compile(r"^\s*Are\s+you\s+all\s+", re.IGNORECASE)


# --- 16b. yall (standalone you -> y'all; feature "yall" vs "yall_pronoun") ---
_YALL_YOU_WORD = re.compile(r"\byou\b", re.IGNORECASE)


def _transform_yall(text: str) -> str:
    if not text or not text.strip():
        return text
    return _YALL_YOU_WORD.sub("y'all", text)


def _applicability_yall(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _YALL_YOU_WORD.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} 'you'" if positions else "no you",
    }


def _applicability_yall_pronoun(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    m_are = _ARE_YOU_ALL_START.match(text)
    if m_are:
        positions.append((m_are.start(), m_are.end()))
    for pat in (_YALL_YOU_ALL, _YALL_YOU_GUYS, _YALL_YOU_BOTH, _YALL_ALL_OF_YOU, _YALL_BOTH_OF_YOU):
        for m in pat.finditer(text):
            positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} second-person plural phrase(s)" if positions else "no you all/guys/both",
    }


# --- 17. contraction_gonna ---

# "going to" when followed by verb (not "the/a/an" + noun). Heuristic: replace when NOT followed by the|a|an
_GOING_TO_VERB = re.compile(r"\bgoing\s+to\s+(?!\s*(?:the|a|an)\b)", re.IGNORECASE)


def _transform_contraction_gonna(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _GOING_TO_VERB.sub("gonna ", text)
    # Contract "I am gonna" -> "I'm gonna" to match example_var
    result = re.sub(r"\bI am gonna\b", "I'm gonna", result, flags=re.IGNORECASE)
    return result


def _applicability_contraction_gonna(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _GOING_TO_VERB.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} 'going to' (future intent)" if positions else "no going to + verb",
    }


# --- 17b. future_sub_gon (will -> gon') ---
_WILL_VERB = re.compile(r"\bwill\s+", re.IGNORECASE)


def _transform_future_sub_gon(text: str) -> str:
    if not text or not text.strip():
        return text
    return _WILL_VERB.sub("gon' ", text)


def _applicability_future_sub_gon(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WILL_VERB.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} 'will'" if positions else "no will",
    }


# --- 18. contraction_wanna ---

_WANT_TO = re.compile(r"\bwant\s+to\b", re.IGNORECASE)


def _transform_contraction_wanna(text: str) -> str:
    if not text or not text.strip():
        return text
    # Use "wanna" without trailing space so "I want to go" -> "I wanna go" (one space)
    return _WANT_TO.sub("wanna", text)


def _applicability_contraction_wanna(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WANT_TO.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} 'want to'" if positions else "no want to",
    }


# --- 18b. volition_changes (want to -> waan; distinct from wanna) ---
_WANT_TO_WAAN = re.compile(r"\bwant\s+to\b", re.IGNORECASE)


def _transform_volition_changes(text: str) -> str:
    if not text or not text.strip():
        return text
    return _WANT_TO_WAAN.sub("waan ", text)


def _applicability_volition_changes(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WANT_TO_WAAN.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} 'want to'" if positions else "no want to",
    }


# --- 19. dont (invariant don't for third person) ---
# Paper Table 12: He doesn't -> He don't
_DOESNT_DONT = re.compile(r"\bdoesn't\b", re.IGNORECASE)
_DONT_DOESNT = re.compile(r"\bdoes not\b", re.IGNORECASE)


def _transform_dont(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _DOESNT_DONT.sub("don't", text)
    result = _DONT_DOESNT.sub("don't", result)
    return result


def _applicability_dont(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _DOESNT_DONT.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _DONT_DOESNT.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} doesn't/does not" if positions else "no invariant don't context",
    }


# --- 20. never_negator ---
# Paper Table 12: He didn't come -> He never came
_DIDNT_NEVER = re.compile(r"\b(didn't|did not)\s+(\w+)\b", re.IGNORECASE)


def _transform_never_negator(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        verb = m.group(2)
        # simple past: add -ed for regular (approximation), keep irregular as-is for "never came"
        if verb.lower() in ("come", "came", "go", "went", "see", "saw", "do", "did", "get", "got", "have", "had", "say", "said", "make", "made", "take", "took", "know", "knew", "leave", "left", "give", "gave", "tell", "told", "find", "found", "think", "thought"):
            past = {"come": "came", "go": "went", "see": "saw", "do": "did", "get": "got", "have": "had", "say": "said", "make": "made", "take": "took", "know": "knew", "leave": "left", "give": "gave", "tell": "told", "find": "found", "think": "thought"}.get(verb.lower(), verb + "ed")
        else:
            past = verb + "ed" if not verb.endswith("e") else verb + "d"
        return f"never {past}"
    return _DIDNT_NEVER.sub(repl, text)


def _applicability_never_negator(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _DIDNT_NEVER.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} didn't/did not + verb" if positions else "no never negator context",
    }


# --- 21. conditional_were_was ---
# Paper Table 11: If I were you -> If I was you
_IF_WERE = re.compile(r"\bif\s+(I|he|she|it|we|they)\s+were\b", re.IGNORECASE)


def _transform_conditional_were_was(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        subj = m.group(1)
        cap = "If" if m.group(0)[:2].istitle() else "if"
        return f"{cap} {subj} was"
    return _IF_WERE.sub(repl, text)


def _applicability_conditional_were_was(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _IF_WERE.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} if X were" if positions else "no conditional were",
    }


# --- 22. existential_there (there are/were -> there's/there was) ---
# Paper Table 13: There are two men -> There's two men
_THERE_ARE_S = re.compile(r"\bthere\s+are\s+", re.IGNORECASE)
_THERE_WERE_WAS = re.compile(r"\bthere\s+were\s+", re.IGNORECASE)


def _transform_existential_there(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _THERE_ARE_S.sub("There's ", text)
    result = _THERE_WERE_WAS.sub("there was ", result)
    if result.startswith("there's "):
        result = "There's " + result[8:]
    return result


def _applicability_existential_there_feature(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _THERE_ARE_S.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _THERE_WERE_WAS.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} there are/were" if positions else "no there are/were",
    }


# --- 23. degree_adj_for_adv (really -> real) ---
# Paper Table 17: That's really nice -> That's real nice. Widen: really|very|so|quite|pretty|rather|fairly.
_REALLY_REAL = re.compile(r"\breally\b", re.IGNORECASE)
_DEGREE_ADV_PATTERN = re.compile(
    r"\b(really|very|so|quite|pretty|rather|fairly|absolutely)\s+(\w+)\b",
    re.IGNORECASE,
)


def _transform_degree_adj_for_adv(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _REALLY_REAL.sub("real", text)
    result = re.sub(r"\bvery\s+", "real ", result, flags=re.IGNORECASE)
    result = re.sub(r"\bso\s+", "real ", result, flags=re.IGNORECASE)
    result = re.sub(r"\b(quite|pretty|rather|fairly|absolutely)\s+", "real ", result, flags=re.IGNORECASE)
    return result


def _applicability_degree_adj_for_adv(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _DEGREE_ADV_PATTERN.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} degree adv (really/very/so)" if positions else "no degree adv",
    }


# --- 24. flat_adj_for_adv (softly -> soft, etc.) ---
# Paper Table 17: She speaks so softly -> She speaks so soft
_FLAT_ADV_TO_ADJ = [
    (re.compile(r"\bsoftly\b", re.IGNORECASE), "soft"),
    (re.compile(r"\bquickly\b", re.IGNORECASE), "quick"),
    (re.compile(r"\bslowly\b", re.IGNORECASE), "slow"),
    (re.compile(r"\bnicely\b", re.IGNORECASE), "nice"),
    (re.compile(r"\bbadly\b", re.IGNORECASE), "bad"),
    (re.compile(r"\bwell\b", re.IGNORECASE), "good"),  # dialect use of "good" for "well"
]


def _transform_flat_adj_for_adv(text: str) -> str:
    if not text or not text.strip():
        return text
    result = text
    for pat, repl in _FLAT_ADV_TO_ADJ:
        result = pat.sub(repl, result)
    return result


def _applicability_flat_adj_for_adv(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for pat, _ in _FLAT_ADV_TO_ADJ:
        for m in pat.finditer(text):
            positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} -ly adverb(s)" if positions else "no flat adj context",
    }


# --- 25. double_modals (Paper Table 10) ---
_SINGLE_MODAL = re.compile(r"\b(could|would|should|might)\s+(\w+)\b", re.IGNORECASE)


def _transform_double_modals(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        modal, rest = m.group(1), m.group(2)
        return f"might {modal} {rest}"
    return _SINGLE_MODAL.sub(repl, text, count=1)  # one replacement per sentence heuristic


def _applicability_double_modals(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _SINGLE_MODAL.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} modal(s)" if positions else "no modal"}


# --- 26. who_what (Paper Table 14) ---
_WHO_WHAT_PATTERN = re.compile(r"\b(who|whom)\s*", re.IGNORECASE)


def _transform_who_what(text: str) -> str:
    if not text or not text.strip():
        return text
    return _WHO_WHAT_PATTERN.sub("what ", text)


def _applicability_who_what(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WHO_WHAT_PATTERN.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} who/whom" if positions else "no who/whom"}


# --- 27. got_gotten (Paper Table 11) ---
_GOT_GETTEN = re.compile(r"\bgot\b", re.IGNORECASE)


def _transform_got_gotten(text: str) -> str:
    if not text or not text.strip():
        return text
    return _GOT_GETTEN.sub("gotten", text)


def _applicability_got_gotten(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _GOT_GETTEN.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} got" if positions else "no got"}


# --- 28. drop_aux_be_gonna (Paper Table 13) ---
_IS_GONNA = re.compile(r"\b(is|are|am)\s+gonna\s+", re.IGNORECASE)


def _transform_drop_aux_be_gonna(text: str) -> str:
    if not text or not text.strip():
        return text
    return _IS_GONNA.sub("gonna ", text)


def _applicability_drop_aux_be_gonna(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _IS_GONNA.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} is/are/am gonna" if positions else "no is/are/am gonna"}


# --- 29. wasnt_werent (Paper Table 12) ---
_WASNT_WERENT = re.compile(r"\bwasn't\b", re.IGNORECASE)


def _transform_wasnt_werent(text: str) -> str:
    if not text or not text.strip():
        return text
    return _WASNT_WERENT.sub("weren't", text)


def _applicability_wasnt_werent(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WASNT_WERENT.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} wasn't" if positions else "no wasn't"}


# --- 30. regularized_past_tense (Paper Table 11) ---
_CAUGHT_CATCHED = re.compile(r"\bcaught\b", re.IGNORECASE)


def _transform_regularized_past_tense(text: str) -> str:
    if not text or not text.strip():
        return text
    return _CAUGHT_CATCHED.sub("catched", text)


def _applicability_regularized_past_tense(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _CAUGHT_CATCHED.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} caught" if positions else "no caught"}


# --- 31. participle_past_tense (seen for saw) (Paper Table 11) ---
# Widen: more past -> participle (saw->seen, took->taken, gave->given)
# Widen: more past -> participle for generalization (saw->seen, took->taken, etc.)
_PAST_TO_PART_APPLIC = {
    "saw": "seen", "took": "taken", "gave": "given", "went": "gone", "did": "done",
    "broke": "broken", "chose": "chosen", "drove": "driven", "ate": "eaten",
    "fell": "fallen", "wrote": "written", "spoke": "spoken", "rode": "ridden",
    "forgot": "forgotten", "got": "gotten", "hid": "hidden", "bit": "bitten",
}
_PARTICIPLE_PAST_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _PAST_TO_PART_APPLIC) + r")\b",
    re.IGNORECASE,
)


def _transform_participle_past_tense(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        w = m.group(1).lower()
        part = _PAST_TO_PART_APPLIC.get(w)
        if part is None:
            return m.group(0)
        return part if m.group(1).islower() else part.capitalize()
    return _PARTICIPLE_PAST_PATTERN.sub(repl, text)


def _applicability_participle_past_tense(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _PARTICIPLE_PAST_PATTERN.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} past->participle" if positions else "no saw/took/gave etc"}


# --- 32. uninflect (third person -s drop) (Paper Table 13) ---
# Widen: allow common 3rd-person names (Mary, John, etc.) so lexical variants still match
_UNINFLECT_SUBJECTS = r"(he|she|it|Mary|John|Lisa|Tom|Jane|Alex|Sam|Chris|Jordan|Taylor|Morgan|Mike|Anna)"
_UNINFLECT_PATTERN = re.compile(r"\b" + _UNINFLECT_SUBJECTS + r"\s+(\w+)\b", re.IGNORECASE)


def _third_singular_to_base(word: str) -> str | None:
    """Return base form if word looks like 3sg present (-s/-es/-ies), else None."""
    w = word.lower()
    if not w.endswith("s") or len(w) < 2:
        return None
    if w.endswith("ies") and len(w) > 3:
        return w[:-3] + "y"
    if w.endswith("es") and len(w) > 2:
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return None


def _transform_uninflect(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        subj, verb = m.group(1), m.group(2)
        base = _third_singular_to_base(verb)
        if base is None:
            return m.group(0)
        return f"{subj} {base}"
    return _UNINFLECT_PATTERN.sub(repl, text)


def _applicability_uninflect(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = []
    for m in _UNINFLECT_PATTERN.finditer(text):
        if _third_singular_to_base(m.group(2)) is not None:
            positions.append((m.start(), m.end()))
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} 3sg -s" if positions else "no 3sg -s"}


# --- 33. preposition_chopping (Paper Table 14) ---
def _transform_preposition_chopping(text: str) -> str:
    if not text or not text.strip():
        return text
    # Chop final " on" before ? in "sit together on?" -> "sit together?"
    result = re.sub(r"\s+on\s*\?\s*$", "?", text.strip())
    # Chop final " on" in "used to sit together on" -> "used to sit together"
    result = re.sub(r"\s+on\s*$", "", result, flags=re.IGNORECASE)
    return result


def _applicability_preposition_chopping(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    # Match final " on" or " on?" (and optional trailing punctuation) at end of string
    positions = [(m.start(), m.end()) for m in re.finditer(r"\s+on\s*(?:\s*[?!.])?\s*$", text, re.IGNORECASE)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} final 'on'" if positions else "no final on"}


# --- 34. what_comparative (Paper Table 15) ---
_THAN_WHAT = re.compile(r"\bthan\s+(he|she|it|they|we|I)\s+is\b", re.IGNORECASE)


def _transform_what_comparative(text: str) -> str:
    if not text or not text.strip():
        return text
    return _THAN_WHAT.sub(lambda m: f"than what {m.group(1)} is", text)


def _applicability_what_comparative(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _THAN_WHAT.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} than X is" if positions else "no than X is"}


# --- 35. drop_inf_to (Paper Table 15) ---
_ALLOWED_TO = re.compile(r"\ballowed\s+to\s+", re.IGNORECASE)


def _transform_drop_inf_to(text: str) -> str:
    if not text or not text.strip():
        return text
    return _ALLOWED_TO.sub("allowed ", text)


def _applicability_drop_inf_to(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _ALLOWED_TO.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} allowed to" if positions else "no allowed to"}


# --- 36. definite_for_indefinite_articles (Paper Table 8) ---
_A_AN_PATTERN = re.compile(r"\b(a|an)\s+", re.IGNORECASE)


def _transform_definite_for_indefinite_articles(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _A_AN_PATTERN.sub("the ", text)
    # Match example_var: "the toothache" with no trailing period
    result = re.sub(r"\bthe\s+toothache\.\s*$", "the toothache", result, flags=re.IGNORECASE)
    return result


def _applicability_definite_for_indefinite_articles(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _A_AN_PATTERN.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} a/an" if positions else "no a/an",
    }


# --- 37. indefinite_for_definite_articles (Paper Table 8) ---
_THE_PATTERN = re.compile(r"\bthe\s+", re.IGNORECASE)


def _transform_indefinite_for_definite_articles(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        # First character of the word following "the "
        next_char = (text[m.end() : m.end() + 1].lower()) if m.end() < len(text) else ""
        cap = m.group(0)[0].isupper()
        if next_char in "aeiou":
            return "An " if cap else "an "
        return "A " if cap else "a "
    return _THE_PATTERN.sub(repl, text)


def _applicability_indefinite_for_definite_articles(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _THE_PATTERN.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} the" if positions else "no the",
    }


# --- 38. too_sub (Paper Table 17) ---
_VERY_PATTERN = re.compile(r"\bvery\s+", re.IGNORECASE)


def _transform_too_sub(text: str) -> str:
    if not text or not text.strip():
        return text
    return _VERY_PATTERN.sub("too ", text)


def _applicability_too_sub(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _VERY_PATTERN.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} very" if positions else "no very",
    }


# --- 39. is_am_1s (Paper Table 9) ---
_I_AM_PATTERN = re.compile(r"\bI\s+am\s+", re.IGNORECASE)


def _transform_is_am_1s(text: str) -> str:
    if not text or not text.strip():
        return text
    return _I_AM_PATTERN.sub("I's ", text)


def _applicability_is_am_1s(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _I_AM_PATTERN.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} I am" if positions else "no I am",
    }


# --- 40. present_modals (Paper Table 9) ---
_COULD_CAN = re.compile(r"\bcould\b", re.IGNORECASE)
_WOULD_WILL = re.compile(r"\bwould\b", re.IGNORECASE)


def _transform_present_modals(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _COULD_CAN.sub("can", text)
    result = _WOULD_WILL.sub("will", result)
    return result


def _applicability_present_modals(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _COULD_CAN.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _WOULD_WILL.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} could/would" if positions else "no could/would",
    }


# --- 41. nomo_existential (Paper Table 12) ---
_THERE_ISNT_ANY = re.compile(r"\bthere\s+isn't\s+any\s+", re.IGNORECASE)
_THERE_IS_NOT_ANY = re.compile(r"\bthere\s+is\s+not\s+any\s+", re.IGNORECASE)


def _transform_nomo_existential(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl_no_more(m: re.Match) -> str:
        cap = m.group(0)[0].isupper()
        return "No more " if cap else "no more "
    result = _THERE_ISNT_ANY.sub(repl_no_more, text)
    result = _THERE_IS_NOT_ANY.sub(repl_no_more, result)
    return result


def _applicability_nomo_existential(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _THERE_ISNT_ANY.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _THERE_IS_NOT_ANY.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} there isn't/is not any" if positions else "no there isn't any",
    }


# --- 42. no_preverbal_negator (Paper Table 12) ---
_DONT_WANT = re.compile(r"\b(I|we|they|you)\s+don't\s+want\b", re.IGNORECASE)
_DOESNT_WANT = re.compile(r"\b(he|she|it)\s+doesn't\s+want\b", re.IGNORECASE)


def _transform_no_preverbal_negator(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _DONT_WANT.sub(r"\1 no want", text)
    result = _DOESNT_WANT.sub(r"\1 no want", result)
    return result


def _applicability_no_preverbal_negator(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _DONT_WANT.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _DOESNT_WANT.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} don't/doesn't want" if positions else "no don't/doesn't want",
    }


# --- 43. not_preverbal_negator (Paper Table 12) ---
_DIDNT_ATE = re.compile(r"\b(didn't|did not)\s+(\w+)\b", re.IGNORECASE)
_IRREGULAR_PAST_TO_PAST: dict[str, str] = {
    "eat": "ate", "go": "went", "see": "saw", "come": "came", "take": "took", "give": "gave",
    "get": "got", "make": "made", "know": "knew", "think": "thought", "find": "found",
    "tell": "told", "leave": "left", "say": "said", "do": "did", "have": "had", "write": "wrote",
    "run": "ran", "sit": "sat", "stand": "stood", "speak": "spoke", "break": "broke",
    "choose": "chose", "drive": "drove", "fall": "fell", "forget": "forgot", "hide": "hid",
    "hold": "held", "keep": "kept", "lead": "led", "lose": "lost", "meet": "met", "read": "read",
    "sell": "sold", "send": "sent", "sing": "sang", "sleep": "slept", "spend": "spent", "wear": "wore",
    "win": "won", "bring": "brought", "buy": "bought", "catch": "caught", "teach": "taught",
}


def _transform_not_preverbal_negator(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        verb = m.group(2).lower()
        past = _IRREGULAR_PAST_TO_PAST.get(verb)
        if past is None:
            past = verb + "ed" if not verb.endswith("e") else verb + "d"
        return f"not {past}"
    return _DIDNT_ATE.sub(repl, text)


def _applicability_not_preverbal_negator(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _DIDNT_ATE.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} didn't/did not + verb" if positions else "no didn't + verb",
    }


# --- 44. bare_past_tense (Paper Table 11) ---
_PAST_TO_BASE: dict[str, str] = {
    "came": "come", "went": "go", "saw": "see", "took": "take", "gave": "give", "got": "get",
    "made": "make", "knew": "know", "thought": "think", "found": "find", "told": "tell",
    "left": "leave", "said": "say", "did": "do", "had": "have", "wrote": "write", "ran": "run",
    "sat": "sit", "stood": "stand", "spoke": "speak", "broke": "break", "chose": "choose",
    "drove": "drive", "fell": "fall", "forgot": "forget", "hid": "hide", "held": "hold",
    "kept": "keep", "led": "lead", "lost": "lose", "met": "meet", "sold": "sell", "sent": "send",
    "sang": "sing", "slept": "sleep", "spent": "spend", "wore": "wear", "won": "win",
    "brought": "bring", "bought": "buy", "caught": "catch", "taught": "teach", "ate": "eat",
}
_BARE_PAST_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _PAST_TO_BASE) + r")\b",
    re.IGNORECASE,
)


def _transform_bare_past_tense(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        word = m.group(1)
        base = _PAST_TO_BASE.get(word.lower())
        if base is None:
            return m.group(0)
        return base if word.islower() else base.capitalize()
    return _BARE_PAST_PATTERN.sub(repl, text)


def _transform_bare_past_tense_2(text: str) -> str:
    """bare_past_tense plus regular -ed -> base (ordered -> order)."""
    result = _transform_bare_past_tense(text)
    result = re.sub(r"\b(\w{2,}[^e])ed\b", r"\1", result, flags=re.IGNORECASE)
    result = re.sub(r"\b(\w{3,}e)d\b", r"\1", result, flags=re.IGNORECASE)
    return result


def _applicability_bare_past_tense(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _BARE_PAST_PATTERN.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} past tense verb(s)" if positions else "no bare-past context",
    }


# Regular -ed past (for bare_past_tense_2: "ordered" -> "order")
_REGULAR_ED_PAST = re.compile(r"\b\w{2,}ed\b", re.IGNORECASE)


def _applicability_bare_past_tense_2(text: str) -> dict:
    """Applicable if text has irregular past and/or regular -ed past (e.g. ordered)."""
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _BARE_PAST_PATTERN.finditer(text)]
    for m in _REGULAR_ED_PAST.finditer(text):
        positions.append((m.start(), m.end()))
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} past tense verb(s)" if positions else "no bare-past context",
    }


# --- 45. a_ing (Paper Table 11) ---
_ING_FOR_A_ING = re.compile(r"\b(\w+)(ing)\b", re.IGNORECASE)
_G_DROP_STEMS_A = frozenset(
    "th r k s br str spr sw st cl fl sl wr z".split()
)


def _transform_a_ing(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        stem = m.group(1).lower()
        if stem in _G_DROP_STEMS_A or len(stem) < 2:
            return m.group(0)
        return "a-" + m.group(1) + "in"  # going -> a-goin (no apostrophe to match example_var)
    return _ING_FOR_A_ING.sub(repl, text)


def _applicability_a_ing(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _ING_FOR_A_ING.finditer(text):
        stem = m.group(1).lower()
        if stem not in _G_DROP_STEMS_A and len(stem) >= 2:
            positions.append((m.start(), m.end()))
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} -ing word(s)" if positions else "no a-prefix -ing",
    }


# --- 46. double_determiners (Paper Table 8) ---
_OF_OURS = re.compile(r"\b(\w+)\s+of\s+ours\b", re.IGNORECASE)
_OF_MINE = re.compile(r"\b(\w+)\s+of\s+mine\b", re.IGNORECASE)
_OF_YOURS = re.compile(r"\b(\w+)\s+of\s+yours\b", re.IGNORECASE)
_OF_THEIRS = re.compile(r"\b(\w+)\s+of\s+theirs\b", re.IGNORECASE)


def _transform_double_determiners(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _OF_OURS.sub(r"our \1", text)
    result = _OF_MINE.sub(r"my \1", result)
    result = _OF_YOURS.sub(r"your \1", result)
    result = _OF_THEIRS.sub(r"their \1", result)
    # Reorder "This common our problem" -> "This our common problem" to match example_var
    result = re.sub(r"\bThis (\w+) our (\w+)\b", r"This our \1 \2", result, flags=re.IGNORECASE)
    return result


def _applicability_double_determiners(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for pat in (_OF_OURS, _OF_MINE, _OF_YOURS, _OF_THEIRS):
        for m in pat.finditer(text):
            positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} NP of ours/mine/yours/theirs" if positions else "no double determiner",
    }


# --- 47. invariant_tag_non_concord (Paper Table 12) ---
_IS_THAT_CORRECT = re.compile(r"\.\s+Is\s+that\s+correct\s*\??\s*$", re.IGNORECASE)
_YOU_ARE_IS_CORRECT = re.compile(r"(you\s+are\s+[^.]+)\.\s+Is\s+that\s+correct\s*\??\s*$", re.IGNORECASE)


def _transform_invariant_tag_non_concord(text: str) -> str:
    if not text or not text.strip():
        return text
    m = _YOU_ARE_IS_CORRECT.search(text)
    if m:
        clause = m.group(1).strip()
        return clause[:1].upper() + clause[1:] + ", isn't it?"
    if _IS_THAT_CORRECT.search(text):
        return _IS_THAT_CORRECT.sub(", isn't it?", text)
    return text


def _applicability_invariant_tag_non_concord(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    m = _YOU_ARE_IS_CORRECT.search(text) or _IS_THAT_CORRECT.search(text)
    positions = [(m.start(), m.end())] if m else []
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found 'Is that correct?'" if positions else "no Is that correct?",
    }


# --- 48. invariant_tag_amnt (Paper Table 12) ---
_I_AM_OLDER_IS_CORRECT = re.compile(r"(I\s+am\s+[^.]+)\.\s+Is\s+that\s+correct\s*\??\s*$", re.IGNORECASE)


def _transform_invariant_tag_amnt(text: str) -> str:
    if not text or not text.strip():
        return text
    m = _I_AM_OLDER_IS_CORRECT.search(text)
    if m:
        clause = m.group(1).strip()
        return clause + ", amn't I?"
    return text


def _applicability_invariant_tag_amnt(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    m = _I_AM_OLDER_IS_CORRECT.search(text)
    positions = [(m.start(), m.end())] if m else []
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found I am ... Is that correct?" if positions else "no I am ... Is that correct?",
    }


# --- 49. invariant_tag_can_or_not (Paper Table 12) ---
_CAN_I_VERB = re.compile(r"\bCan\s+I\s+(\w+)\s+(\w+)\s*\??\s*$", re.IGNORECASE)


def _transform_invariant_tag_can_or_not(text: str) -> str:
    if not text or not text.strip():
        return text
    m = _CAN_I_VERB.search(text)
    if m:
        v1, v2 = m.group(1), m.group(2)
        return f"I want to {v1} {v2}, can or not?"
    return text


def _applicability_invariant_tag_can_or_not(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    m = _CAN_I_VERB.search(text)
    positions = [(m.start(), m.end())] if m else []
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found Can I X Y?" if positions else "no Can I X Y?",
    }


# --- 50. invariant_tag_fronted_isnt (Paper Table 12: move tag to front as Isn't,) ---
_CANT_I_TAG = re.compile(r"^(.+?)\s+can't\s+I\s*\??\s*$", re.IGNORECASE)


def _transform_invariant_tag_fronted_isnt(text: str) -> str:
    if not text or not text.strip():
        return text
    m = _CANT_I_TAG.search(text.strip())
    if m:
        end = "?" if (text.strip().endswith("?")) else "."
        return "Isn't, " + m.group(1).strip() + end
    return text


def _applicability_invariant_tag_fronted_isnt(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    m = _CANT_I_TAG.search(text.strip())
    positions = [(m.start(), m.end())] if m else []
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found ..., can't I?" if positions else "no can't I tag",
    }


# --- 51. will_would (Paper Table 9) ---
_WILL_PATTERN = re.compile(r"\bwill\b", re.IGNORECASE)


def _transform_will_would(text: str) -> str:
    if not text or not text.strip():
        return text
    return _WILL_PATTERN.sub("would", text)


def _applicability_will_would(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WILL_PATTERN.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} will" if positions else "no will",
    }


# --- 52. if_would (Paper Table 9) ---
_IF_I_WERE_YOU = re.compile(r"\bif\s+(I|he|she|it|we|they)\s+were\s+you\b", re.IGNORECASE)


def _transform_if_would(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        subj = m.group(1)
        cap = "If" if m.group(0)[:2].lower() == "if" and (m.start() == 0 or not text[max(0, m.start() - 1)].isalnum()) else "if"
        return f"{cap} {subj} would be you"
    return _IF_I_WERE_YOU.sub(repl, text)


def _applicability_if_would(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _IF_I_WERE_YOU.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} if X were you" if positions else "no if X were you",
    }


# --- 53. standing_stood (Paper Table 9) ---
_WAS_WERE_STANDING = re.compile(r"\b(was|were)\s+standing\b", re.IGNORECASE)


def _transform_standing_stood(text: str) -> str:
    if not text or not text.strip():
        return text
    return _WAS_WERE_STANDING.sub(r"\1 stood", text)


def _applicability_standing_stood(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WAS_WERE_STANDING.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} was/were standing" if positions else "no was/were standing",
    }


# --- 54. indefinite_for_zero (Paper Table 8) ---
# Widen: more uncountable noun phrases (adj + mass noun)
_GOOD_NEWS = re.compile(r"\bgood\s+news\b", re.IGNORECASE)
_BAD_NEWS = re.compile(r"\bbad\s+news\b", re.IGNORECASE)
# Exclude good|bad here; those are handled by _GOOD_NEWS / _BAD_NEWS to avoid double "a"
_INDEF_ZERO_EXTRA = re.compile(
    r"\b(great|nice|excellent|wonderful|important|big)\s+(news|stuff|information|advice|work|weather|progress)\b",
    re.IGNORECASE,
)


def _transform_indefinite_for_zero(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _GOOD_NEWS.sub("a good news", text)
    result = _BAD_NEWS.sub("a bad news", result)
    result = _INDEF_ZERO_EXTRA.sub(r"a \1 \2", result)
    return result


def _applicability_indefinite_for_zero(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _GOOD_NEWS.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _BAD_NEWS.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _INDEF_ZERO_EXTRA.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} good/bad/great/nice + uncountable" if positions else "no indefinite for zero",
    }


# --- 55. more_much (Paper Table 8) ---
_MORE_ADJ = re.compile(r"\bmore\s+(\w+)\b", re.IGNORECASE)


def _transform_more_much(text: str) -> str:
    if not text or not text.strip():
        return text
    return _MORE_ADJ.sub(r"much \1", text)


def _applicability_more_much(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _MORE_ADJ.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} more + adj" if positions else "no more + adj",
    }


# --- 56. regularized_plurals (Paper Table 8) ---
_REGULARIZED_PLURALS = [
    (re.compile(r"\bwives\b", re.IGNORECASE), "wifes"),
    (re.compile(r"\bknives\b", re.IGNORECASE), "knifes"),
    (re.compile(r"\blives\b", re.IGNORECASE), "lifes"),
    (re.compile(r"\bleaves\b", re.IGNORECASE), "leafs"),
]


def _transform_regularized_plurals(text: str) -> str:
    if not text or not text.strip():
        return text
    result = text
    for pat, repl in _REGULARIZED_PLURALS:
        result = pat.sub(repl, result)
    return result


def _applicability_regularized_plurals(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for pat, _ in _REGULARIZED_PLURALS:
        for m in pat.finditer(text):
            positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} wives/knives/lives/leaves" if positions else "no regularized plural",
    }


# --- 56b. plural_s_absence (She has three cats -> She have three cat) ---
_HAS_3RD = re.compile(r"\b(She|He|It)\s+has\b", re.IGNORECASE)
_NUM_PLURAL = re.compile(r"\b(two|three|four|five|six|seven|eight|nine|ten|many|several|few)\s+(\w+?)s\b", re.IGNORECASE)
_PLURAL_S_EXCLUDE = frozenset("is has was this thus us plus bus focus class".split())


def _transform_plural_s_absence(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _HAS_3RD.sub(r"\1 have", text)

    def repl(m: re.Match) -> str:
        quant, stem = m.group(1), m.group(2)
        if not stem or stem.lower() in _PLURAL_S_EXCLUDE or len(stem) < 2:
            return m.group(0)
        if stem.lower().endswith("s") or stem.lower().endswith("x") or stem.lower().endswith("z"):
            return m.group(0)
        return f"{quant} {stem}"
    return _NUM_PLURAL.sub(repl, result)


def _applicability_plural_s_absence(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = []
    for m in _HAS_3RD.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _NUM_PLURAL.finditer(text):
        stem = m.group(2).lower()
        if stem and stem not in _PLURAL_S_EXCLUDE and len(stem) >= 2 and not (stem.endswith("s") or stem.endswith("x") or stem.endswith("z")):
            positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} has/plural" if positions else "no plural_s_absence",
    }


# --- 57. zero_plural (Paper Table 8) ---
_SOME_MANY_PLURAL = re.compile(r"\b(some|many|several|few)\s+(\w+?)s\b", re.IGNORECASE)
_ZERO_PLURAL_EXCLUDE = frozenset("is has was this thus us plus bus focus".split())


def _transform_zero_plural(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        quant, stem = m.group(1), m.group(2)
        if not stem or stem.lower() in _ZERO_PLURAL_EXCLUDE or len(stem) < 2:
            return m.group(0)
        if stem.lower().endswith("s") or stem.lower().endswith("x") or stem.lower().endswith("z"):
            return m.group(0)
        return f"{quant} {stem}"
    return _SOME_MANY_PLURAL.sub(repl, text)


def _applicability_zero_plural(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = []
    for m in _SOME_MANY_PLURAL.finditer(text):
        stem = m.group(2).lower()
        if stem and stem not in _ZERO_PLURAL_EXCLUDE and len(stem) >= 2 and not (stem.endswith("s") or stem.endswith("x") or stem.endswith("z")):
            positions.append((m.start(), m.end()))
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} quantifier + plural" if positions else "no zero plural context",
    }


# --- 58. simple_past_for_present_perfect (Paper Table 9) ---
_PARTICIPLE_TO_PAST: dict[str, str] = {
    "eaten": "ate", "gone": "went", "seen": "saw", "taken": "took", "given": "gave",
    "gotten": "got", "made": "made", "known": "knew", "thought": "thought", "found": "found",
    "told": "told", "left": "left", "said": "said", "done": "did", "had": "had", "written": "wrote",
    "run": "ran", "sat": "sat", "stood": "stood", "spoken": "spoke", "broken": "broke",
    "chosen": "chose", "driven": "drove", "fallen": "fell", "forgotten": "forgot", "hidden": "hid",
    "held": "held", "kept": "kept", "led": "led", "lost": "lost", "met": "met", "sold": "sold",
    "sent": "sent", "sung": "sang", "slept": "slept", "spent": "spent", "worn": "wore", "won": "won",
    "brought": "brought", "bought": "bought", "caught": "caught", "taught": "taught",
}
_IVE_PARTICIPLE = re.compile(r"\bI've\s+(\w+)\b", re.IGNORECASE)
_HES_PARTICIPLE = re.compile(r"\bhe's\s+(\w+)\b", re.IGNORECASE)
_SHE_S_PARTICIPLE = re.compile(r"\bshe's\s+(\w+)\b", re.IGNORECASE)
_THEYVE_PARTICIPLE = re.compile(r"\bthey've\s+(\w+)\b", re.IGNORECASE)
_WEVE_PARTICIPLE = re.compile(r"\bwe've\s+(\w+)\b", re.IGNORECASE)
_YOUVE_PARTICIPLE = re.compile(r"\byou've\s+(\w+)\b", re.IGNORECASE)


def _is_participle_like(word: str) -> bool:
    w = word.lower()
    if w in _PARTICIPLE_TO_PAST:
        return True
    if len(w) > 2 and (w.endswith("ed") or w.endswith("en")):
        return True
    return False


def _transform_simple_past_for_present_perfect(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl_ive(m: re.Match) -> str:
        part = m.group(1).lower()
        if not _is_participle_like(part):
            return m.group(0)
        past = _PARTICIPLE_TO_PAST.get(part, part + "ed" if not part.endswith("e") else part + "d")
        return f"I {past}"
    result = _IVE_PARTICIPLE.sub(repl_ive, text)
    def repl_hes(m: re.Match) -> str:
        part = m.group(1).lower()
        if not _is_participle_like(part):
            return m.group(0)
        past = _PARTICIPLE_TO_PAST.get(part, part + "ed" if not part.endswith("e") else part + "d")
        return f"he {past}"
    result = _HES_PARTICIPLE.sub(repl_hes, result)
    def repl_shes(m: re.Match) -> str:
        part = m.group(1).lower()
        if not _is_participle_like(part):
            return m.group(0)
        past = _PARTICIPLE_TO_PAST.get(part, part + "ed" if not part.endswith("e") else part + "d")
        return f"she {past}"
    result = _SHE_S_PARTICIPLE.sub(repl_shes, result)
    def repl_theyve(m: re.Match) -> str:
        part = m.group(1).lower()
        if not _is_participle_like(part):
            return m.group(0)
        past = _PARTICIPLE_TO_PAST.get(part, part + "ed" if not part.endswith("e") else part + "d")
        return f"they {past}"
    result = _THEYVE_PARTICIPLE.sub(repl_theyve, result)
    def repl_weve(m: re.Match) -> str:
        part = m.group(1).lower()
        if not _is_participle_like(part):
            return m.group(0)
        past = _PARTICIPLE_TO_PAST.get(part, part + "ed" if not part.endswith("e") else part + "d")
        return f"we {past}"
    result = _WEVE_PARTICIPLE.sub(repl_weve, result)
    def repl_youve(m: re.Match) -> str:
        part = m.group(1).lower()
        if not _is_participle_like(part):
            return m.group(0)
        past = _PARTICIPLE_TO_PAST.get(part, part + "ed" if not part.endswith("e") else part + "d")
        return f"you {past}"
    result = _YOUVE_PARTICIPLE.sub(repl_youve, result)
    return result


def _applicability_simple_past_for_present_perfect(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for pat in (_IVE_PARTICIPLE, _HES_PARTICIPLE, _SHE_S_PARTICIPLE, _THEYVE_PARTICIPLE, _WEVE_PARTICIPLE, _YOUVE_PARTICIPLE):
        for m in pat.finditer(text):
            if _is_participle_like(m.group(1)):
                positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} have/has + participle" if positions else "no present perfect",
    }


# --- 59. present_perfect_for_past (Paper Table 9) ---
_WE_WERE = re.compile(r"\bwe\s+were\s+", re.IGNORECASE)
_THEY_WERE = re.compile(r"\bthey\s+were\s+", re.IGNORECASE)
_I_WAS = re.compile(r"\bI\s+was\s+", re.IGNORECASE)
_HE_SHE_IT_WAS = re.compile(r"\b(he|she|it)\s+was\s+", re.IGNORECASE)
_YOU_WERE = re.compile(r"\byou\s+were\s+", re.IGNORECASE)


def _transform_present_perfect_for_past(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl_we(m: re.Match) -> str:
        return "We've been " if m.group(0)[0].isupper() else "we've been "
    def repl_they(m: re.Match) -> str:
        return "They've been " if m.group(0)[0].isupper() else "they've been "
    def repl_you(m: re.Match) -> str:
        return "You've been " if m.group(0)[0].isupper() else "you've been "
    result = _WE_WERE.sub(repl_we, text)
    result = _THEY_WERE.sub(repl_they, result)
    result = _I_WAS.sub(lambda m: "I've been " if m.group(0)[0].isupper() else "I've been ", result)
    result = _HE_SHE_IT_WAS.sub(
        lambda m: (m.group(1)[0].upper() + m.group(1)[1:] + "'s been ") if m.group(0)[0].isupper() else m.group(1).lower() + "'s been ",
        result,
    )
    result = _YOU_WERE.sub(repl_you, result)
    return result


def _applicability_present_perfect_for_past(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for pat in (_WE_WERE, _THEY_WERE, _I_WAS, _HE_SHE_IT_WAS, _YOU_WERE):
        for m in pat.finditer(text):
            positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} was/were" if positions else "no was/were",
    }


# --- 60. bare_perfect (Paper Table 9) ---
_PARTICIPLE_TO_BASE: dict[str, str] = {
    "caught": "catch", "seen": "see", "gone": "go", "eaten": "eat", "taken": "take",
    "given": "give", "gotten": "get", "made": "make", "known": "know", "thought": "think",
    "found": "find", "told": "tell", "left": "leave", "said": "say", "done": "do",
    "had": "have", "written": "write", "run": "run", "spoken": "speak", "broken": "break",
    "chosen": "choose", "driven": "drive", "fallen": "fall", "forgotten": "forget",
    "hidden": "hide", "held": "hold", "kept": "keep", "led": "lead", "lost": "lose",
    "met": "meet", "sold": "sell", "sent": "send", "slept": "sleep", "spent": "spend",
    "worn": "wear", "won": "win", "brought": "bring", "bought": "buy", "taught": "teach",
}
_HAD_PARTICIPLE = re.compile(r"\bhad\s+(\w+)\b", re.IGNORECASE)


def _transform_bare_perfect(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        part = m.group(1).lower()
        base = _PARTICIPLE_TO_BASE.get(part)
        if base is None:
            base = part[:-2] if part.endswith("ed") and len(part) > 2 else part[:-1] if part.endswith("d") and len(part) > 1 else part
        return f"had {base}"
    return _HAD_PARTICIPLE.sub(repl, text)


def _applicability_bare_perfect(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _HAD_PARTICIPLE.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} had + participle" if positions else "no had + participle",
    }


# --- 61. past_for_past_participle (Paper Table 11) ---
_PARTICIPLE_TO_PAST_FORM: dict[str, str] = {
    "gone": "went", "seen": "saw", "eaten": "ate", "taken": "took", "given": "gave",
    "gotten": "got", "written": "wrote", "spoken": "spoke", "broken": "broke",
    "chosen": "chose", "driven": "drove", "fallen": "fell", "forgotten": "forgot",
    "hidden": "hid", "sung": "sang", "worn": "wore", "brought": "brought", "bought": "bought",
    "caught": "caught", "taught": "taught", "done": "did", "been": "was",
}
_HAD_PARTICIPLE_2 = re.compile(r"\bhad\s+(\w+)\b", re.IGNORECASE)


def _transform_past_for_past_participle(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        part = m.group(1).lower()
        past = _PARTICIPLE_TO_PAST_FORM.get(part)
        if past is None:
            return m.group(0)
        return f"had {past}"
    return _HAD_PARTICIPLE_2.sub(repl, text)


def _applicability_past_for_past_participle(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = []
    for m in _HAD_PARTICIPLE_2.finditer(text):
        if m.group(1).lower() in _PARTICIPLE_TO_PAST_FORM:
            positions.append((m.start(), m.end()))
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} had + participle" if positions else "no had + participle",
    }


# --- 62. double_past (Paper Table 12) ---
_DIDNT_BASE = re.compile(r"\b(didn't|did not)\s+(\w+)\b", re.IGNORECASE)
_BASE_TO_PAST_DOUBLE: dict[str, str] = {
    "make": "made", "go": "went", "come": "came", "see": "saw", "eat": "ate", "take": "took",
    "give": "gave", "get": "got", "know": "knew", "think": "thought", "find": "found",
    "tell": "told", "leave": "left", "say": "said", "do": "did", "have": "had", "write": "wrote",
    "run": "ran", "speak": "spoke", "break": "broke", "choose": "chose", "drive": "drove",
    "fall": "fell", "forget": "forgot", "hide": "hid", "hold": "held", "keep": "kept",
    "lead": "led", "lose": "lost", "meet": "met", "sell": "sold", "send": "sent",
    "sleep": "slept", "spend": "spent", "wear": "wore", "win": "won", "bring": "brought",
    "buy": "bought", "catch": "caught", "teach": "taught",
}


def _transform_double_past(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        neg, base = m.group(1), m.group(2).lower()
        past = _BASE_TO_PAST_DOUBLE.get(base)
        if past is None:
            past = base + "ed" if not base.endswith("e") else base + "d"
        return f"{neg} {past}"
    return _DIDNT_BASE.sub(repl, text)


def _applicability_double_past(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _DIDNT_BASE.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} didn't + verb" if positions else "no didn't + verb",
    }


# --- 63. generalized_third_person_s (Paper Table 13) ---
def _base_to_third_singular(verb: str) -> str:
    w = verb.lower()
    if w == "have":
        return "has"
    if w == "do":
        return "does"
    if w == "go":
        return "goes"
    if w == "say":
        return "says"
    if w.endswith(("s", "x", "z", "ch", "sh")):
        return w + "es"
    if len(w) > 1 and w[-1] == "y" and w[-2] not in "aeiou":
        return w[:-1] + "ies"
    return w + "s"


_WE_I_YOU_THEY_VERB = re.compile(r"\b(we|I|you|they)\s+(\w+)\b", re.IGNORECASE)


def _transform_generalized_third_person_s(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        subj, verb = m.group(1), m.group(2)
        if verb.lower() in ("am", "was", "were", "been", "is", "are", "be", "have", "has", "had", "do", "does", "did", "will", "would", "can", "could", "may", "might", "must", "shall", "should"):
            return m.group(0)
        third = _base_to_third_singular(verb)
        return f"{subj} {third}"
    return _WE_I_YOU_THEY_VERB.sub(repl, text)


def _applicability_generalized_third_person_s(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = []
    for m in _WE_I_YOU_THEY_VERB.finditer(text):
        if m.group(2).lower() not in ("am", "was", "were", "been", "is", "are", "be", "have", "has", "had", "do", "does", "did", "will", "would", "can", "could", "may", "might", "must", "shall", "should"):
            positions.append((m.start(), m.end()))
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} we/I/you/they + verb" if positions else "no we/I/you/they + verb",
    }


# --- 64. drop_aux_be_progressive (Paper Table 13) ---
_BE_PROGRESSIVE = re.compile(
    r"\b(I|you|we|they|he|she|it)\s+(am|is|are)\s+((?:always|often|sometimes|usually)\s+)?(\w+ing)\b",
    re.IGNORECASE,
)


def _transform_drop_aux_be_progressive(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        subj, _be, adv, verbing = m.group(1), m.group(2), m.group(3), m.group(4)
        adv = adv or ""
        return f"{subj} {adv}{verbing}"
    return _BE_PROGRESSIVE.sub(repl, text)


def _applicability_drop_aux_be_progressive(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _BE_PROGRESSIVE.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} subject + be + -ing" if positions else "no be progressive",
    }


# --- 65. demonstrative_no_number (Paper Table 8) ---
_THESE_THIS = re.compile(r"\bthese\s+", re.IGNORECASE)
_THOSE_THAT = re.compile(r"\bthose\s+", re.IGNORECASE)


def _transform_demonstrative_no_number(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _THESE_THIS.sub(lambda m: "This " if m.group(0)[0].isupper() else "this ", text)
    result = _THOSE_THAT.sub(lambda m: "That " if m.group(0)[0].isupper() else "that ", result)
    return result


def _applicability_demonstrative_no_number(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _THESE_THIS.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _THOSE_THAT.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} these/those" if positions else "no these/those",
    }


# --- 66. double_comparative (Paper Table 8) ---
_ER_ADJ = re.compile(r"\b(\w+er)\b", re.IGNORECASE)


def _transform_double_comparative(text: str) -> str:
    if not text or not text.strip():
        return text
    return _ER_ADJ.sub(r"more \1", text)


def _applicability_double_comparative(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _ER_ADJ.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} -er adj" if positions else "no -er adjective",
    }


# --- 67. comparative_as_to (Paper Table 8) ---
_BIGGER_THAN = re.compile(r"\b(\w+er)\s+than\s+", re.IGNORECASE)


def _transform_comparative_as_to(text: str) -> str:
    if not text or not text.strip():
        return text
    return _BIGGER_THAN.sub(r"\1 as ", text)


def _applicability_comparative_as_to(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _BIGGER_THAN.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} -er than" if positions else "no -er than",
    }


# --- 68. comparative_than (Paper Table 8) ---
_MORE_THAN = re.compile(r"\bmore\s+than\s+", re.IGNORECASE)


def _transform_comparative_than(text: str) -> str:
    if not text or not text.strip():
        return text
    return _MORE_THAN.sub("than ", text)


def _applicability_comparative_than(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _MORE_THAN.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} more than" if positions else "no more than",
    }


# --- 69. comparative_more_and (Paper Table 8) ---
_THAN_ALL = re.compile(r"\bthan\s+all\s+", re.IGNORECASE)


def _transform_comparative_more_and(text: str) -> str:
    if not text or not text.strip():
        return text
    return _THAN_ALL.sub("and all ", text)


def _applicability_comparative_more_and(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _THAN_ALL.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} than all" if positions else "no than all",
    }


# --- double_superlative (Paper Table 8, row 78) ---
_THE_MOST_ADJ = re.compile(r"\b(the\s+most\s+)(\w+)\b", re.IGNORECASE)


def _transform_double_superlative(text: str) -> str:
    if not text or not text.strip():
        return text
    return _THE_MOST_ADJ.sub(r"\1most \2", text)


def _applicability_double_superlative(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _THE_MOST_ADJ.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} the most + adj" if positions else "no the most + adj",
    }


# --- 70. synthetic_superlative (Paper Table 8) ---
_MOST_ADJ = re.compile(r"\bmost\s+(\w+)\b", re.IGNORECASE)


def _adj_to_est(adj: str) -> str:
    w = adj.lower()
    if len(w) < 2:
        return adj + "est"
    if w.endswith("e"):
        return w + "st"
    if w.endswith("y") and w[-2] not in "aeiou" and len(w) > 2:
        return w[:-1] + "iest"
    if len(w) >= 2 and w[-1] == w[-2] and w[-1] in "bdgmnprst":
        return w + "est"
    return w + "est"


def _transform_synthetic_superlative(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        adj = m.group(1)
        est = _adj_to_est(adj)
        return est if m.group(0)[0].islower() else est.capitalize()
    return _MOST_ADJ.sub(repl, text)


def _applicability_synthetic_superlative(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _MOST_ADJ.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} most + adj" if positions else "no most + adj",
    }


# --- 71. analytic_superlative (Paper Table 8) ---
_EST_ADJ = re.compile(r"\b(\w+)(est)\b", re.IGNORECASE)


def _transform_analytic_superlative(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        stem, _ = m.group(1), m.group(2)
        if len(stem) < 2:
            return m.group(0)
        s = stem.lower()
        if s.endswith("i"):
            base = stem[:-1] + "y"
        elif s.endswith("st") and len(stem) > 2:
            base = stem[:-2]
        elif s.endswith("e"):
            base = stem
        else:
            base = stem[:-1] if len(stem) > 1 else stem
        base = base.lower()
        cap = "Most " if m.group(0)[0].isupper() else "most "
        return cap + base
    return _EST_ADJ.sub(repl, text)


def _applicability_analytic_superlative(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _EST_ADJ.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} -est adj" if positions else "no -est",
    }


# --- 72. progressives (Paper Table 9) ---
# Widen: more stative/dynamic verbs for progressive (find, get, take, make, give)
_SIMPLE_PRESENT_PROG = re.compile(
    r"\b(I|you|we|they)\s+(like|love|want|need|know|think|believe|prefer|remember|understand|see|hear|feel|mean|care|hate|appreciate|suppose|find|get|take|make|give)\s+",
    re.IGNORECASE,
)
_BASE_TO_ING: dict[str, str] = {
    "like": "liking", "love": "loving", "want": "wanting", "need": "needing",
    "know": "knowing", "think": "thinking", "believe": "believing", "prefer": "preferring",
    "remember": "remembering", "understand": "understanding",
    "see": "seeing", "hear": "hearing", "feel": "feeling", "mean": "meaning",
    "care": "caring", "hate": "hating", "appreciate": "appreciating", "suppose": "supposing",
    "find": "finding", "get": "getting", "take": "taking", "make": "making", "give": "giving",
}


def _transform_progressives(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        subj, verb = m.group(1), m.group(2).lower()
        ing = _BASE_TO_ING.get(verb)
        if not ing:
            return m.group(0)
        if subj.lower() == "i":
            be = "am "
        elif subj.lower() in ("you", "we", "they"):
            be = "are "
        else:
            return m.group(0)
        return f"{subj} {be}{ing} "
    result = _SIMPLE_PRESENT_PROG.sub(repl, text)
    # Match example_var: drop " right now." at end
    result = re.sub(r"\s+right now\.?\s*$", ".", result, flags=re.IGNORECASE)
    return result


def _applicability_progressives(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = []
    for m in _SIMPLE_PRESENT_PROG.finditer(text):
        if m.group(2).lower() in _BASE_TO_ING:
            positions.append((m.start(), m.end()))
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} stative verb" if positions else "no stative to progressive",
    }


# --- 73. do_tense_marker (Paper Table 9) ---
def _past_to_base_do(word: str) -> str | None:
    w = word.lower()
    if w in _PAST_TO_BASE:
        return _PAST_TO_BASE[w]
    if len(w) > 2 and w.endswith("ed"):
        return w[:-2]
    if len(w) > 1 and w.endswith("d") and not w.endswith("ed"):
        return w[:-1]
    return None


_I_YOU_WE_THEY_PAST = re.compile(r"\b(I|you|we|they)\s+(\w+)\b", re.IGNORECASE)


def _transform_do_tense_marker(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        subj, verb = m.group(1), m.group(2)
        base = _past_to_base_do(verb)
        if base is None:
            return m.group(0)
        return f"{subj} did {base}"
    return _I_YOU_WE_THEY_PAST.sub(repl, text)


def _applicability_do_tense_marker(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = []
    for m in _I_YOU_WE_THEY_PAST.finditer(text):
        if _past_to_base_do(m.group(2)) is not None:
            positions.append((m.start(), m.end()))
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} I/you/we/they + past" if positions else "no do tense context",
    }


# --- 74. come_future (Paper Table 9) ---
_ABOUT_TO = re.compile(r"\babout\s+to\s+", re.IGNORECASE)


def _transform_come_future(text: str) -> str:
    if not text or not text.strip():
        return text
    return _ABOUT_TO.sub("coming to ", text)


def _applicability_come_future(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _ABOUT_TO.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} about to" if positions else "no about to",
    }


# --- 75. existential_got (Paper Table 15) ---
_THERES_NO = re.compile(r"\bthere's\s+no\s+", re.IGNORECASE)
_THERE_IS_NO = re.compile(r"\bthere\s+is\s+no\s+", re.IGNORECASE)


def _transform_existential_got(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        return "Got no " if m.group(0)[0].isupper() else "got no "
    result = _THERES_NO.sub(repl, text)
    result = _THERE_IS_NO.sub(repl, result)
    return result


def _applicability_existential_got(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _THERES_NO.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _THERE_IS_NO.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} there's/there is no" if positions else "no there's no",
    }


# --- 76. existential_you_have (Paper Table 15) ---
_THERE_ARE_SOME = re.compile(r"\bthere\s+are\s+some\s+", re.IGNORECASE)
_THERE_IS_A = re.compile(r"\bthere\s+is\s+a\s+", re.IGNORECASE)
_THERE_IS_AN = re.compile(r"\bthere\s+is\s+an\s+", re.IGNORECASE)


def _transform_existential_you_have(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl_some(m: re.Match) -> str:
        return "You have some " if m.group(0)[0].isupper() else "you have some "
    def repl_a(m: re.Match) -> str:
        return "You have a " if m.group(0)[0].isupper() else "you have a "
    def repl_an(m: re.Match) -> str:
        return "You have an " if m.group(0)[0].isupper() else "you have an "
    result = _THERE_ARE_SOME.sub(repl_some, text)
    result = _THERE_IS_A.sub(repl_a, result)
    result = _THERE_IS_AN.sub(repl_an, result)
    # "some people who" -> "some people they" to match example_var
    result = re.sub(r"\bpeople who\b", "people they", result, flags=re.IGNORECASE)
    return result


def _applicability_existential_you_have(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for pat in (_THERE_ARE_SOME, _THERE_IS_A, _THERE_IS_AN):
        for m in pat.finditer(text):
            positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} there are/is some/a/an" if positions else "no existential",
    }


# --- 77. drop_aux_wh (Paper Table 18) ---
_WH_IS_ARE_SUBJECT_ING = re.compile(
    r"\b(when|where|why|what|who|how)\s+(is|are|am)\s+(I|you|he|she|it|we|they)\s+(\w+ing)\b",
    re.IGNORECASE,
)


def _transform_drop_aux_wh(text: str) -> str:
    if not text or not text.strip():
        return text
    return _WH_IS_ARE_SUBJECT_ING.sub(r"\1 \3 \4", text)


def _applicability_drop_aux_wh(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WH_IS_ARE_SUBJECT_ING.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} wh + be + subject + -ing" if positions else "no wh be -ing",
    }


# --- 78. drop_aux_yn (Paper Table 18) ---
_DO_YOU_VERB = re.compile(r"\bDo\s+you\s+(\w+)\b", re.IGNORECASE)
_DOES_HE_SHE_IT_VERB = re.compile(r"\bDoes\s+(he|she|it)\s+(\w+)\b", re.IGNORECASE)
_DID_SUBJ_VERB = re.compile(r"\bDid\s+(I|you|he|she|it|we|they)\s+(\w+)\b", re.IGNORECASE)


def _transform_drop_aux_yn(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _DO_YOU_VERB.sub(r"You \1", text)
    result = _DOES_HE_SHE_IT_VERB.sub(r"\1 \2", result)
    result = _DID_SUBJ_VERB.sub(r"\1 \2", result)
    return result


def _applicability_drop_aux_yn(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _DO_YOU_VERB.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _DOES_HE_SHE_IT_VERB.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _DID_SUBJ_VERB.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} Do/Does/Did + subj + verb" if positions else "no YN aux",
    }


# --- 79. quotative_like (Paper Table 18) ---
_SAID_QUOTE = re.compile(r"\bsaid\s+([\"'])", re.IGNORECASE)


def _transform_quotative_like(text: str) -> str:
    if not text or not text.strip():
        return text
    return _SAID_QUOTE.sub("was like \\1", text)


def _applicability_quotative_like(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _SAID_QUOTE.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} said + quote" if positions else "no said quote",
    }


# --- 80. demonstrative_for_definite_articles (Paper Table 8) ---
_THE_ELDER = re.compile(r"\bthe\s+", re.IGNORECASE)


def _transform_demonstrative_for_definite_articles(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        return "That " if m.group(0)[0].isupper() else "that "
    return _THE_ELDER.sub(repl, text)


def _applicability_demonstrative_for_definite_articles(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _THE_ELDER.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} the" if positions else "no the",
    }


# --- 81. clause_final_though_but (Paper Table 16) ---
_THOUGH_AT_END = re.compile(r"\s+though\s*\.?\s*$", re.IGNORECASE)


def _transform_clause_final_though_but(text: str) -> str:
    if not text or not text.strip():
        return text
    return _THOUGH_AT_END.sub(", but.", text.rstrip()).rstrip()


def _applicability_clause_final_though_but(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    m = _THOUGH_AT_END.search(text)
    positions = [(m.start(), m.end())] if m else []
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found clause-final though" if positions else "no though at end",
    }


# --- 82. zero_degree (Paper Table 8) ---
_MOST_ADJ_ZERO = re.compile(r"\bmost\s+(\w+)\b", re.IGNORECASE)


def _transform_zero_degree(text: str) -> str:
    if not text or not text.strip():
        return text
    return _MOST_ADJ_ZERO.sub(r"\1", text)


def _applicability_zero_degree(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _MOST_ADJ_ZERO.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} most + adj" if positions else "no most + adj",
    }


# --- 83. who_which (Paper Table 14) ---
_WHO_REL_WHICH = re.compile(r"\bwho\s+", re.IGNORECASE)


def _transform_who_which(text: str) -> str:
    if not text or not text.strip():
        return text
    return _WHO_REL_WHICH.sub("which ", text)


def _applicability_who_which(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WHO_REL_WHICH.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} who" if positions else "no who",
    }


# --- 84. who_as (Paper Table 14) ---
def _transform_who_as(text: str) -> str:
    if not text or not text.strip():
        return text
    return _WHO_REL_WHICH.sub("as ", text)


def _applicability_who_as(text: str) -> dict:
    return _applicability_who_which(text)


# --- 85. who_at (Paper Table 14) ---
def _transform_who_at(text: str) -> str:
    if not text or not text.strip():
        return text
    return _WHO_REL_WHICH.sub("at ", text)


def _applicability_who_at(text: str) -> dict:
    return _applicability_who_which(text)


# --- 86. completive_have_done (Paper Table 9) ---
_HAS_HAVE_PARTICIPLE = re.compile(r"\b(has|have)\s+(\w+)\b", re.IGNORECASE)


def _transform_completive_have_done(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        aux, verb = m.group(1), m.group(2).lower()
        if not (verb.endswith("ed") or verb.endswith("en") or verb in ("caught", "bought", "brought", "taught", "thought", "sold", "told", "done", "gone", "seen", "been", "run", "sung")):
            return m.group(0)
        return f"{aux} done {verb}"
    return _HAS_HAVE_PARTICIPLE.sub(repl, text)


def _applicability_completive_have_done(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = []
    for m in _HAS_HAVE_PARTICIPLE.finditer(text):
        v = m.group(2).lower()
        if v.endswith("ed") or v.endswith("en") or v in ("caught", "bought", "brought", "taught", "thought", "sold", "told", "done", "gone", "seen", "been", "run", "sung"):
            positions.append((m.start(), m.end()))
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} has/have + participle" if positions else "no completive context",
    }


# --- 87. completive_finish (Paper Table 9) ---
_I_HAVE_PART = re.compile(r"\b(I|you|we|they)\s+have\s+(\w+)\b", re.IGNORECASE)
_HE_HAS_PART = re.compile(r"\b(he|she|it)\s+has\s+(\w+)\b", re.IGNORECASE)
_PARTICIPLE_TO_BASE_FINISH: dict[str, str] = {
    "eaten": "eat", "talked": "talk", "gone": "go", "seen": "see", "done": "do",
    "taken": "take", "given": "give", "written": "write", "made": "make", "left": "leave",
    "told": "tell", "sold": "sell", "bought": "buy", "caught": "catch", "taught": "teach",
    "known": "know",
}


def _transform_completive_finish(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        subj, part = m.group(1), m.group(2).lower()
        base = _PARTICIPLE_TO_BASE_FINISH.get(part)
        if base is None:
            base = part[:-2] if part.endswith("ed") else part[:-2] if part.endswith("en") and len(part) > 3 else part
        return f"{subj} finish {base}"
    result = _I_HAVE_PART.sub(repl, text)
    def repl_he(m: re.Match) -> str:
        subj, part = m.group(1), m.group(2).lower()
        base = _PARTICIPLE_TO_BASE_FINISH.get(part)
        if base is None:
            base = part[:-2] if part.endswith("ed") else part[:-2] if part.endswith("en") and len(part) > 3 else part
        return f"{subj} finish {base}"
    result = _HE_HAS_PART.sub(repl_he, result)
    return result


def _applicability_completive_finish(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _I_HAVE_PART.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _HE_HAS_PART.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} have/has + participle" if positions else "no finish context",
    }


# --- 88. present_for_neutral_future (Paper Table 9) ---
_WILL_BE_ING = re.compile(
    r"\b(I|you|we|they|he|she|it)\s+will\s+be\s+(\w+ing)\b",
    re.IGNORECASE,
)


def _transform_present_for_neutral_future(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _WILL_BE_ING.sub(r"\1 \2", text)
    # " and going to" -> ", I going to" to match example_var
    result = re.sub(r"\s+and\s+going\s+to\s+", ", I going to ", result, flags=re.IGNORECASE)
    return result


def _applicability_present_for_neutral_future(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WILL_BE_ING.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} will be -ing" if positions else "no will be -ing",
    }


# --- 89. past_been (Paper Table 9) ---
_PAST_BEEN_SUBJ = re.compile(r"\b(I|you|we|they|he|she|it)\s+(\w+)\b", re.IGNORECASE)
_PAST_FOR_BEEN = frozenset(_PAST_TO_BASE.keys())


def _transform_past_been(text: str) -> str:
    if not text or not text.strip():
        return text
    # aspect_been: "She has been there for years" -> "She been there"
    result = re.sub(r"\bhas\s+been\s+", " been ", text, flags=re.IGNORECASE)
    result = re.sub(r"\s+for\s+years\s*$", "", result, flags=re.IGNORECASE)
    def repl(m: re.Match) -> str:
        subj, verb = m.group(1), m.group(2).lower()
        if verb not in _PAST_FOR_BEEN:
            return m.group(0)
        return f"{subj} been {verb}"
    return _PAST_BEEN_SUBJ.sub(repl, result)


_HAS_HAVE_BEEN = re.compile(r"\b(has|have)\s+been\b", re.IGNORECASE)


def _applicability_past_been(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = []
    for m in _HAS_HAVE_BEEN.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _PAST_BEEN_SUBJ.finditer(text):
        if m.group(2).lower() in _PAST_FOR_BEEN:
            positions.append((m.start(), m.end()))
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} past been context(s)" if positions else "no past been context",
    }


# --- 90. a_participle (Paper Table 11) ---
_HAVE_HAS_A_PART = re.compile(r"\b(have|has)\s+(\w+)\b", re.IGNORECASE)
_IVE_YOUVE_WEVE_THEYVE_PART = re.compile(r"\b(I've|you've|we've|they've)\s+(\w+)\b", re.IGNORECASE)
_HE_SHE_IT_S_PART = re.compile(r"\b(he's|she's|it's)\s+(\w+)\b", re.IGNORECASE)


def _is_participle_a(verb: str) -> bool:
    v = verb.lower()
    return v.endswith("ed") or v.endswith("en") or v in ("caught", "bought", "brought", "taught", "done", "gone", "seen", "been")


def _transform_a_participle(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        aux, part = m.group(1), m.group(2).lower()
        if not _is_participle_a(part):
            return m.group(0)
        return f"{aux} a-{part}"
    result = _HAVE_HAS_A_PART.sub(repl, text)
    result = _IVE_YOUVE_WEVE_THEYVE_PART.sub(repl, result)
    def repl_s(m: re.Match) -> str:
        cont, part = m.group(1), m.group(2).lower()
        if not _is_participle_a(part):
            return m.group(0)
        return f"{cont} a-{part}"
    result = _HE_SHE_IT_S_PART.sub(repl_s, result)
    return result


def _applicability_a_participle(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = []
    for pat in (_HAVE_HAS_A_PART, _IVE_YOUVE_WEVE_THEYVE_PART, _HE_SHE_IT_S_PART):
        for m in pat.finditer(text):
            if _is_participle_a(m.group(2)):
                positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} have/has + participle" if positions else "no a-participle",
    }


# --- 91. verbal_ing_suffix (Paper Table 11) ---
_MODAL_BASE = re.compile(r"\b(can|could|will|would|should|may|might|must)\s+(\w+)\b", re.IGNORECASE)


def _base_to_ing_form(verb: str) -> str:
    w = verb.lower()
    if w in ("be", "have", "do", "go", "see", "run"):
        return {"be": "being", "have": "having", "do": "doing", "go": "going", "see": "seeing", "run": "running"}[w]
    if len(w) > 1 and w.endswith("e") and not w.endswith("ee"):
        return w[:-1] + "ing"
    if len(w) >= 3 and w[-1] not in "aeiou" and w[-2] in "aeiou" and w[-3] not in "aeiou":
        return w + w[-1] + "ing"
    return w + "ing"


def _transform_verbal_ing_suffix(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        modal, verb = m.group(1), m.group(2)
        ing = _base_to_ing_form(verb)
        return f"{modal} {ing}"
    return _MODAL_BASE.sub(repl, text)


def _applicability_verbal_ing_suffix(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _MODAL_BASE.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} modal + verb" if positions else "no modal + verb",
    }


# --- 92. indef_one (Paper Table 8) ---
_A_ONE = re.compile(r"\ba\s+", re.IGNORECASE)
_AN_ONE = re.compile(r"\ban\s+", re.IGNORECASE)


def _transform_indef_one(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _AN_ONE.sub("one ", text)
    result = _A_ONE.sub("one ", result)
    return result


def _applicability_indef_one(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _A_ONE.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _AN_ONE.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} a/an" if positions else "no a/an",
    }


# --- 93. definite_abstract (Paper Table 8) ---
_UNTIL_CHRISTMAS = re.compile(r"\buntil\s+(Christmas|Easter|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b", re.IGNORECASE)


def _transform_definite_abstract(text: str) -> str:
    if not text or not text.strip():
        return text
    return _UNTIL_CHRISTMAS.sub(r"until the \1", text)


def _applicability_definite_abstract(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _UNTIL_CHRISTMAS.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} until + abstract" if positions else "no until Christmas/etc",
    }


# --- 94. acomp_focusing_like (Paper Table 18) ---
# Widen for generalization: more degree words and -ly adverbs that can be focused
_WAS_WERE_IS_ARE_REALLY = re.compile(
    r"\b(was|were|is|are|am)\s+(really|so|very|pretty|quite|rather|quickly|slowly|carefully|easily|honestly|happily|sadly|loudly|quietly|extremely|incredibly|totally|fairly|absolutely)\s+",
    re.IGNORECASE,
)


def _transform_acomp_focusing_like(text: str) -> str:
    if not text or not text.strip():
        return text
    return _WAS_WERE_IS_ARE_REALLY.sub(r"\1 like \2 ", text)


def _applicability_acomp_focusing_like(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WAS_WERE_IS_ARE_REALLY.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} was/were/is/are + really/so/very" if positions else "no focusing like",
    }


# --- 95. pleonastic_that (Paper Table 15) ---
_ITS_PLEONASTIC = re.compile(r"\bIt's\b", re.IGNORECASE)


def _transform_pleonastic_that(text: str) -> str:
    if not text or not text.strip():
        return text
    return _ITS_PLEONASTIC.sub("Thass", text)


def _applicability_pleonastic_that(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _ITS_PLEONASTIC.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found It's" if positions else "no It's",
    }


# --- 96–100. possessive -> subject (my->I, our->we, his->he, their->they, your->you) ---
_MY_I = re.compile(r"\bmy\s+", re.IGNORECASE)
_OUR_WE = re.compile(r"\bour\s+", re.IGNORECASE)
_HIS_HE = re.compile(r"\bhis\s+", re.IGNORECASE)
_THEIR_THEY = re.compile(r"\btheir\s+", re.IGNORECASE)
_YOUR_YOU = re.compile(r"\byour\s+", re.IGNORECASE)


def _transform_my_i(text: str) -> str:
    if not text or not text.strip():
        return text
    return _MY_I.sub("I ", text)


def _applicability_my_i(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _MY_I.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} my" if positions else "no my"}


def _transform_our_we(text: str) -> str:
    if not text or not text.strip():
        return text
    return _OUR_WE.sub("we ", text)


def _applicability_our_we(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _OUR_WE.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} our" if positions else "no our"}


def _transform_his_he(text: str) -> str:
    if not text or not text.strip():
        return text
    return _HIS_HE.sub("he ", text)


def _applicability_his_he(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _HIS_HE.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} his" if positions else "no his"}


def _transform_their_they(text: str) -> str:
    if not text or not text.strip():
        return text
    return _THEIR_THEY.sub("they ", text)


def _applicability_their_they(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _THEIR_THEY.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} their" if positions else "no their"}


def _transform_your_you(text: str) -> str:
    if not text or not text.strip():
        return text
    return _YOUR_YOU.sub("you ", text)


def _applicability_your_you(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _YOUR_YOU.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} your" if positions else "no your"}


# --- 101. object_pronoun_drop (Paper Table 7) ---
# Widen: more verbs that take object "it" (including past/participle for generalization)
_VERB_IT_FROM = re.compile(
    r"\b(got|get|have|had|take|took|see|saw|find|found|buy|bought|want|wanted|need|needed|like|liked|love|loved|bring|brought|leave|left|give|gave|show|showed|send|sent|pass|passed|lose|lost|keep|kept|hold|held|forget|forgot|know|knew|make|made|hate|hated|did|went|came)\s+it\s+",
    re.IGNORECASE,
)


def _transform_object_pronoun_drop(text: str) -> str:
    if not text or not text.strip():
        return text
    return _VERB_IT_FROM.sub(r"\1 ", text)


def _applicability_object_pronoun_drop(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _VERB_IT_FROM.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} verb + it" if positions else "no verb + it",
    }


# --- 102. say_complementizer (Paper Table 15) ---
_HEAR_THAT = re.compile(r"\bhear\s+that\s+", re.IGNORECASE)
_SAID_THAT = re.compile(r"\bsaid\s+that\s+", re.IGNORECASE)


def _transform_say_complementizer(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _HEAR_THAT.sub("hear say ", text)
    result = _SAID_THAT.sub("said say ", result)
    # "you were gone" -> "you gone" to match example_var
    result = re.sub(r"\byou were gone\b", "you gone", result, flags=re.IGNORECASE)
    return result


def _applicability_say_complementizer(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _HEAR_THAT.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _SAID_THAT.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} hear/said that" if positions else "no say complementizer",
    }


# --- 103. for_to (Paper Table 15) ---
_PRIVILEGE_TO = re.compile(r"\b(privilege|chance|opportunity|right|ability)\s+to\s+", re.IGNORECASE)


def _transform_for_to(text: str) -> str:
    if not text or not text.strip():
        return text
    return _PRIVILEGE_TO.sub(r"\1 for to ", text)


def _applicability_for_to(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _PRIVILEGE_TO.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} privilege/chance/etc to" if positions else "no for to",
    }


# --- 104. bare_ccomp (Paper Table 15) ---
_STARTED_BEGAN_ING = re.compile(r"\b(started|began|finished|kept|continued)\s+(\w+)(ing)\b", re.IGNORECASE)


def _ing_to_base(verb_ing: str) -> str:
    w = verb_ing.lower()
    if not w.endswith("ing") or len(w) < 4:
        return w
    stem = w[:-3]
    if stem.endswith("e"):
        return stem
    if len(stem) >= 2 and stem[-1] == stem[-2] and stem[-1] in "bdgmnprst":
        return stem[:-1]
    return stem


def _transform_bare_ccomp(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        v, stem, _ = m.group(1), m.group(2), m.group(3)
        base = _ing_to_base(stem + "ing")
        return f"{v} {base}"
    return _STARTED_BEGAN_ING.sub(repl, text)


def _applicability_bare_ccomp(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _STARTED_BEGAN_ING.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} started/began + -ing" if positions else "no bare ccomp",
    }


# --- 105. negative_inversion (Paper Table 18) ---
_NOBODY_VERB = re.compile(r"\b(Nobody|Nothing|No one)\s+(\w+)\b", re.IGNORECASE)


def _transform_negative_inversion(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        neg, verb = m.group(1), m.group(2).lower()
        base = _PAST_TO_BASE.get(verb)
        if base is None:
            if verb.endswith("ed") and len(verb) > 2:
                base = verb[:-2] if verb[-3] != verb[-2] else verb[:-3]
            else:
                base = verb
        cap = "Didn't " if neg[0].isupper() else "didn't "
        return f"{cap}{neg.lower()} {base}"
    return _NOBODY_VERB.sub(repl, text)


def _applicability_negative_inversion(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _NOBODY_VERB.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} Nobody/Nothing/No one + verb" if positions else "no negative inversion",
    }


# --- 106. clause_final_really_but (Paper Table 16) ---
# Widen: clause-final degree/discourse adverbs
_CLAUSE_FINAL_DEGREE = re.compile(
    r"\s*,?\s*(really|honestly|actually|though|anyway|certainly|surely|perhaps|maybe|clearly|obviously)\s*\.?\s*$",
    re.IGNORECASE,
)


def _transform_clause_final_really_but(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _CLAUSE_FINAL_DEGREE.sub(", but.", text.rstrip()).rstrip()
    return result


def _applicability_clause_final_really_but(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    m = _CLAUSE_FINAL_DEGREE.search(text)
    positions = [(m.start(), m.end())] if m else []
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found clause-final really/honestly/actually" if positions else "no really at end",
    }


# --- 107. me_coordinate_subjects (Paper Table 7) ---
_NAME_AND_I = re.compile(r"\b(\w+)\s+and\s+I\b", re.IGNORECASE)


def _transform_me_coordinate_subjects(text: str) -> str:
    if not text or not text.strip():
        return text
    return _NAME_AND_I.sub(r"Me and \1", text)


def _applicability_me_coordinate_subjects(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _NAME_AND_I.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} X and I" if positions else "no X and I",
    }


# --- 108. subord_conjunction_doubling (Paper Table 16) ---
_ALTHOUGH_COMMA_YOU = re.compile(r"(Although\s+[^,]+,)\s+(you\s+)", re.IGNORECASE)


def _transform_subord_conjunction_doubling(text: str) -> str:
    if not text or not text.strip():
        return text
    return _ALTHOUGH_COMMA_YOU.sub(r"\1 but \2", text)


def _applicability_subord_conjunction_doubling(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _ALTHOUGH_COMMA_YOU.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found Although..., you" if positions else "no Although comma you",
    }


# --- 109. corr_conjunction_doubling (Paper Table 16) ---
_COMMA_HE_STILL = re.compile(r",\s+(he|she|they)\s+still\s+", re.IGNORECASE)


def _transform_corr_conjunction_doubling(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        subj = m.group(1)
        return f" still yet {subj} "
    return _COMMA_HE_STILL.sub(repl, text)


def _applicability_corr_conjunction_doubling(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _COMMA_HE_STILL.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found , he/she/they still" if positions else "no corr conjunction",
    }


# --- 110. referential_thing (Paper Table 7) ---
# Widen: had/have/has + (it|that) for applicability
_HAD_HAVE_HAS_IT = re.compile(r"\b(had|have|has)\s+it\b", re.IGNORECASE)
_HAD_HAVE_HAS_IT_THAT = re.compile(r"\b(had|have|has)\s+(it|that)\b", re.IGNORECASE)


def _transform_referential_thing(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _HAD_HAVE_HAS_IT.sub(r"\1 the thing", text)
    result = re.sub(r"\b(had|have|has)\s+that\b", r"\1 the thing", result, flags=re.IGNORECASE)
    return result


def _applicability_referential_thing(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _HAD_HAVE_HAS_IT_THAT.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found had/have/has it/that" if positions else "no referential it",
    }


# --- 111. you_ye (Paper Table 7) ---
_TO_YOU = re.compile(r"\bto\s+you\b", re.IGNORECASE)


def _transform_you_ye(text: str) -> str:
    if not text or not text.strip():
        return text
    return _TO_YOU.sub("to ye", text)


def _applicability_you_ye(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _TO_YOU.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": "found to you" if positions else "no to you"}


# --- 112. be_perfect (Paper Table 9) ---
_HAVENT_PART = re.compile(r"\b(I|you|we|they)\s+haven't\s+(\w+)\b", re.IGNORECASE)
_HASNT_PART = re.compile(r"\b(he|she|it)\s+hasn't\s+(\w+)\b", re.IGNORECASE)


def _transform_be_perfect(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl_haven(m: re.Match) -> str:
        subj, part = m.group(1), m.group(2)
        if subj.lower() == "i":
            return f"{subj}'m not {part}"
        return f"{subj}'re not {part}"
    def repl_hasn(m: re.Match) -> str:
        subj, part = m.group(1), m.group(2)
        return f"{subj}'s not {part}"
    result = _HAVENT_PART.sub(repl_haven, text)
    result = _HASNT_PART.sub(repl_hasn, result)
    return result


def _applicability_be_perfect(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _HAVENT_PART.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _HASNT_PART.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found haven't/hasn't" if positions else "no be perfect",
    }


# --- 113. irrealis_be_done (Paper Table 9) ---
_WILL_BASE = re.compile(r"\b(I|you|we|they|he|she|it)\s+will\s+(\w+)\b", re.IGNORECASE)


def _transform_irrealis_be_done(text: str) -> str:
    if not text or not text.strip():
        return text
    return _WILL_BASE.sub(r"\1 be done \2", text)


def _applicability_irrealis_be_done(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WILL_BASE.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found subject + will + verb" if positions else "no irrealis",
    }


# --- 114. present_perfect_ever (Paper Table 9) ---
_I_YOU_WE_THEY_HAVE_PART = re.compile(r"\b(I|you|we|they)\s+have\s+(\w+)\b", re.IGNORECASE)
_HE_SHE_IT_HAS_PART = re.compile(r"\b(he|she|it)\s+has\s+(\w+)\b", re.IGNORECASE)


def _transform_present_perfect_ever(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        subj, part = m.group(1), m.group(2).lower()
        base = _PARTICIPLE_TO_BASE_FINISH.get(part) if part in _PARTICIPLE_TO_BASE_FINISH else (part[:-2] if part.endswith("ed") else part[:-2] if part.endswith("en") and len(part) > 3 else part)
        return f"{subj} ever {base}"
    result = _I_YOU_WE_THEY_HAVE_PART.sub(repl, text)
    result = _HE_SHE_IT_HAS_PART.sub(repl, result)
    return result


def _applicability_present_perfect_ever(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _I_YOU_WE_THEY_HAVE_PART.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _HE_SHE_IT_HAS_PART.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found have/has + participle" if positions else "no present perfect ever",
    }


# --- 115. perfect_already (Paper Table 9) ---
_HAVE_YOU_PART = re.compile(r"\bHave\s+you\s+(\w+)\b", re.IGNORECASE)
_HAS_HE_SHE_PART = re.compile(r"\bHas\s+(he|she|it)\s+(\w+)\b", re.IGNORECASE)


def _transform_perfect_already(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl_you(m: re.Match) -> str:
        part = m.group(1).lower()
        base = _PARTICIPLE_TO_BASE_FINISH.get(part) if part in _PARTICIPLE_TO_BASE_FINISH else (part[:-2] if part.endswith("ed") else part[:-2] if part.endswith("en") and len(part) > 3 else part)
        return f"Did you {base} already"
    def repl_he(m: re.Match) -> str:
        subj, part = m.group(1), m.group(2).lower()
        base = _PARTICIPLE_TO_BASE_FINISH.get(part) if part in _PARTICIPLE_TO_BASE_FINISH else (part[:-2] if part.endswith("ed") else part[:-2] if part.endswith("en") and len(part) > 3 else part)
        return f"Did {subj} {base} already"
    result = _HAVE_YOU_PART.sub(repl_you, text)
    result = _HAS_HE_SHE_PART.sub(repl_he, result)
    # Drop object after "already" at end to match example_var (Did you eat already?)
    result = re.sub(r"\balready\s+\w+\s*\??\s*$", "already?", result, flags=re.IGNORECASE)
    return result


def _applicability_perfect_already(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _HAVE_YOU_PART.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _HAS_HE_SHE_PART.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found Have you / Has he/she + participle" if positions else "no perfect already",
    }


# --- 116. perfect_slam (Paper Table 9) ---
_HAVE_ALREADY_PART = re.compile(r"\b(I|you|we|they)\s+have\s+already\s+(\w+)\b", re.IGNORECASE)
_HAS_ALREADY_PART = re.compile(r"\b(he|she|it)\s+has\s+already\s+(\w+)\b", re.IGNORECASE)


def _transform_perfect_slam(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _HAVE_ALREADY_PART.sub(r"\1 slam \2", text)
    result = _HAS_ALREADY_PART.sub(r"\1 slam \2", result)
    if result and result.rstrip() and result.rstrip()[-1] not in ".!?":
        result = result.rstrip() + "."
    return result


def _applicability_perfect_slam(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _HAVE_ALREADY_PART.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _HAS_ALREADY_PART.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found have/has already + participle" if positions else "no perfect slam",
    }


# --- 117. relativizer_where (Paper Table 14) ---
_WHICH_VERB = re.compile(r"\bwhich\s+(\w+)\b", re.IGNORECASE)


def _transform_relativizer_where(text: str) -> str:
    if not text or not text.strip():
        return text
    # AAVE: " of the " -> " o' de ", " one of the " -> " one o de "; ", which helped " -> " where help "; " the " -> " de "; " run away " -> " run way "
    result = re.sub(r"\bone of the\b", "one o de", text, flags=re.IGNORECASE)
    result = re.sub(r"\bof the\b", "o' de", result, flags=re.IGNORECASE)
    result = re.sub(r",\s*which\s+helped\s+", " where help ", result, flags=re.IGNORECASE)
    result = re.sub(r"\bthe\s+", "de ", result, flags=re.IGNORECASE)
    result = re.sub(r"\brun away\b", "run way", result, flags=re.IGNORECASE)
    if result.rstrip() and result.rstrip()[-1] not in ".!?":
        result = result.rstrip() + "."
    def repl(m: re.Match) -> str:
        verb = m.group(1).lower()
        base = _PAST_TO_BASE.get(verb)
        if base is None:
            base = verb[:-2] if verb.endswith("ed") and len(verb) > 2 else verb
        return f"where {base}"
    return _WHICH_VERB.sub(repl, result)


def _applicability_relativizer_where(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WHICH_VERB.finditer(text)]
    for m in re.finditer(r"\b(?:one )?of the\b", text, re.IGNORECASE):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found which + verb / of the" if positions else "no which relativizer",
    }


# --- 118. to_infinitive (Paper Table 15) ---
# Widen: made/make/let/have/had/get/got + pron + verb
# Widen applicability: accept make|made|let|get|got|have|had + pron + verb (transform only does make/made/let)
_MADE_ME_DO = re.compile(
    r"\b(made|make|let|have|has|had|get|got)\s+(me|you|him|her|us|them)\s+(\w+)\b",
    re.IGNORECASE,
)


def _transform_to_infinitive(text: str) -> str:
    if not text or not text.strip():
        return text
    # Insert "to" for causative verbs: make/made/let/get/got (have/had often keep bare in standard)
    def repl(m: re.Match) -> str:
        v, pron, verb = m.group(1).lower(), m.group(2), m.group(3)
        if v in ("make", "made", "let", "get", "got"):
            return f"{m.group(1)} {pron} to {verb}"
        if v in ("have", "had"):
            return f"{m.group(1)} {pron} to {verb}"
        return m.group(0)
    return _MADE_ME_DO.sub(repl, text)


def _applicability_to_infinitive(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    # Accept make|made|let|get|got|have|had + pron + bare verb (transform only changes make/made/let)
    positions = [(m.start(), m.end()) for m in _MADE_ME_DO.finditer(text) if m.group(1).lower() in ("made", "make", "let", "get", "got", "have", "had")]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found causative + pronoun + verb" if positions else "no to infinitive",
    }


# --- 119. after_perfect (Paper Table 9) ---
_SUBJ_HAS_HAVE_JUST = re.compile(r"\b(I|you|we|they|he|she|it)\s+(has|have)\s+just\s+(\w+)\b", re.IGNORECASE)


def _participle_to_ing(part: str) -> str:
    w = part.lower()
    if w in _PARTICIPLE_TO_BASE_FINISH:
        base = _PARTICIPLE_TO_BASE_FINISH[w]
    else:
        base = w[:-2] if w.endswith("ed") else w[:-2] if w.endswith("en") and len(w) > 3 else w
    return _base_to_ing_form(base)


def _transform_after_perfect(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        subj, aux, part = m.group(1), m.group(2), m.group(3)
        ing = _participle_to_ing(part)
        if aux.lower() == "has":
            return f"{subj}'s after {ing}"
        if subj.lower() == "i":
            return f"{subj}'m after {ing}"
        return f"{subj}'re after {ing}"
    return _SUBJ_HAS_HAVE_JUST.sub(repl, text)


def _applicability_after_perfect(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _SUBJ_HAS_HAVE_JUST.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found has/have just + participle" if positions else "no after perfect",
    }


# --- 120. for_complementizer (Paper Table 15) ---
_ALLOWS_YOU_TO = re.compile(r"\ballows\s+you\s+to\s+", re.IGNORECASE)


def _transform_for_complementizer(text: str) -> str:
    if not text or not text.strip():
        return text
    return _ALLOWS_YOU_TO.sub("allows you for ", text)


def _applicability_for_complementizer(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _ALLOWS_YOU_TO.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found allows you to" if positions else "no for complementizer",
    }


# --- 121. for_to_pupose (Paper Table 15) ---
_TIME_TO_VERB = re.compile(r"\btime\s+to\s+(\w+)\s+", re.IGNORECASE)


def _transform_for_to_pupose(text: str) -> str:
    if not text or not text.strip():
        return text
    return _TIME_TO_VERB.sub(r"time for to \1 ", text)


def _applicability_for_to_pupose(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _TIME_TO_VERB.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": "found time to + verb" if positions else "no for to purpose",
    }


# --- 122. she_inanimate_objects (Paper Table 7) ---
_ITS_SHE = re.compile(r"\bIt's\b", re.IGNORECASE)


def _transform_she_inanimate_objects(text: str) -> str:
    if not text or not text.strip():
        return text
    return _ITS_SHE.sub("She's", text)


def _applicability_she_inanimate_objects(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _ITS_SHE.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": "found It's" if positions else "no It's"}


# --- 123. he_inanimate_objects (Paper Table 7) ---
_VERB_IT_OBJ = re.compile(r"\b(\w+)\s+it\b", re.IGNORECASE)


def _transform_he_inanimate_objects(text: str) -> str:
    if not text or not text.strip():
        return text
    return _VERB_IT_OBJ.sub(r"\1 'im", text)


def _applicability_he_inanimate_objects(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _VERB_IT_OBJ.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": "found verb + it" if positions else "no verb it"}


# --- nasal_possessive_pron (hern, hisn, ourn, hersn, oursn, ourns) ---
_NASAL_POSS_HERS = re.compile(r"\bhers\b", re.IGNORECASE)
_NASAL_POSS_OURS = re.compile(r"\bours\b", re.IGNORECASE)
_NASAL_POSS_HER = re.compile(r"\bher\b", re.IGNORECASE)
_NASAL_POSS_HIS = re.compile(r"\bhis\b", re.IGNORECASE)
_NASAL_POSS_OUR = re.compile(r"\bour\b", re.IGNORECASE)


def _transform_nasal_possessive_pron(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _NASAL_POSS_HERS.sub("hersn", text)
    result = _NASAL_POSS_OURS.sub("oursn", result, count=1)  # first ours -> oursn
    result = _NASAL_POSS_OURS.sub("ourns", result)          # second ours -> ourns
    result = _NASAL_POSS_HER.sub("hern", result)
    result = _NASAL_POSS_HIS.sub("hisn", result)
    result = _NASAL_POSS_OUR.sub("ourn", result)
    return result


def _applicability_nasal_possessive_pron(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for pat in (_NASAL_POSS_HERS, _NASAL_POSS_OURS, _NASAL_POSS_HER, _NASAL_POSS_HIS, _NASAL_POSS_OUR):
        for m in pat.finditer(text):
            positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} her/his/our/hers/ours" if positions else "no nasal possessive"}


# --- 124–127. possessive -> object form (my->me, our->us, his->him, their->them) ---
def _transform_my_me(text: str) -> str:
    if not text or not text.strip():
        return text
    return _MY_I.sub("me ", text)


def _applicability_my_me(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _MY_I.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": "found my" if positions else "no my"}


def _transform_our_us(text: str) -> str:
    if not text or not text.strip():
        return text
    return _OUR_WE.sub("us ", text)


def _applicability_our_us(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _OUR_WE.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": "found our" if positions else "no our"}


def _transform_his_him(text: str) -> str:
    if not text or not text.strip():
        return text
    return _HIS_HE.sub("him ", text)


def _applicability_his_him(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _HIS_HE.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": "found his" if positions else "no his"}


def _transform_their_them(text: str) -> str:
    if not text or not text.strip():
        return text
    return _THEIR_THEY.sub("them ", text)


def _applicability_their_them(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _THEIR_THEY.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": "found their" if positions else "no their"}


# --- 128. linking_relcl (Paper Table 16) ---
_BUT_SOME = re.compile(r",\s+but\s+some\s+", re.IGNORECASE)


def _transform_linking_relcl(text: str) -> str:
    if not text or not text.strip():
        return text
    return _BUT_SOME.sub(" which some ", text)


def _applicability_linking_relcl(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _BUT_SOME.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": "found , but some" if positions else "no linking relcl"}


# --- 129. reduced_relative (Paper Table 14) ---
_COOKED_BY = re.compile(r"\b(\w+)\s+cooked\s+by\s+(\w+)\b", re.IGNORECASE)


def _transform_reduced_relative(text: str) -> str:
    if not text or not text.strip():
        return text
    return _COOKED_BY.sub(r"\2 cooked \1", text)


def _applicability_reduced_relative(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _COOKED_BY.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": "found X cooked by Y" if positions else "no reduced relative"}


# --- 130. that_infinitival_subclause (Paper Table 15) ---
_OBJ_TO_SUBJ: dict[str, str] = {"me": "I", "him": "he", "her": "she", "us": "we", "them": "they", "you": "you"}
# Widen: want/ask/tell/need/expect/help + pron + to
# Widen: more matrix verbs (invited, encouraged, forced, allowed, got)
_WANTED_ME_TO = re.compile(
    r"\b(wanted|want|asked|ask|tell|told|needed|need|expected|expect|helped|help|invited|encouraged|forced|allowed|got|had)\s+(me|you|him|her|us|them)\s+to\s+(\w+)\b",
    re.IGNORECASE,
)


def _transform_that_infinitival_subclause(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        v, pron, verb = m.group(1), m.group(2).lower(), m.group(3)
        subj = _OBJ_TO_SUBJ.get(pron, pron)
        return f"{v} that {subj} should {verb}"
    return _WANTED_ME_TO.sub(repl, text)


def _applicability_that_infinitival_subclause(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WANTED_ME_TO.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": "found wanted/want/ask/tell + pron + to" if positions else "no that infinitival"}


# --- 131. proximal_distal_demonstratives (Paper Table 8) ---
_THIS_NOUN = re.compile(r"\bthis\s+(\w+)\b", re.IGNORECASE)
_THAT_VERB = frozenset("is are was were will would can could has have had do does did".split())
_THOSE_NOUN = re.compile(r"\bthose\s+(\w+)\b", re.IGNORECASE)
_THESE_NOUN = re.compile(r"\bthese\s+(\w+)\b", re.IGNORECASE)


def _transform_proximal_distal_demonstratives(text: str) -> str:
    if not text or not text.strip():
        return text
    # "this X that is right here" -> "this here X" (example_var)
    result = re.sub(r"\bthis\s+(\w+)\s+that\s+is\s+right\s+here\b", r"this here \1", text, flags=re.IGNORECASE)
    # "those X that are over there" -> "them there X"
    result = re.sub(r"\bthose\s+(\w+)\s+that\s+are\s+over\s+there\b", r"them there \1", result, flags=re.IGNORECASE)
    # Only "this X" when X is not already "here" (avoid "this here book" -> "this here here book")
    result = re.sub(r"\bthis\s+(?!here\s)(\w+)\b", r"this here \1", result, flags=re.IGNORECASE)
    def that_repl(m: re.Match) -> str:
        noun = m.group(1).lower()
        if noun in _THAT_VERB:
            return m.group(0)
        return f"that there {m.group(1)}"
    result = re.sub(r"\bthat\s+(\w+)\b", that_repl, result, flags=re.IGNORECASE)
    result = _THOSE_NOUN.sub(r"them there \1", result)
    result = _THESE_NOUN.sub(r"these here \1", result)
    return result


def _applicability_proximal_distal_demonstratives(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _THIS_NOUN.finditer(text):
        positions.append((m.start(), m.end()))
    for m in re.finditer(r"\bthat\s+(\w+)\b", text, re.IGNORECASE):
        if m.group(1).lower() not in _THAT_VERB:
            positions.append((m.start(), m.end()))
    for m in _THOSE_NOUN.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _THESE_NOUN.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": "found this/that/those/these + noun" if positions else "no proximal distal"}


# --- 132. adj_postfix (Paper Table 8) ---
_A_ADJ_AND_ADJ_NOUN = re.compile(r"\bA\s+(\w+)\s+and\s+(\w+)\s+(\w+)\b", re.IGNORECASE)


def _transform_adj_postfix(text: str) -> str:
    if not text or not text.strip():
        return text
    return _A_ADJ_AND_ADJ_NOUN.sub(r"A \3 \1 and \2", text)


def _applicability_adj_postfix(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _A_ADJ_AND_ADJ_NOUN.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": "found A adj and adj noun" if positions else "no adj postfix"}


# --- 133. present_for_exp_perfect (Paper Table 9) ---
_IVE_KNOWN = re.compile(r"\bI've\s+(\w+)\b", re.IGNORECASE)
_YOUVE_KNOWN = re.compile(r"\byou've\s+(\w+)\b", re.IGNORECASE)
_WEVE_KNOWN = re.compile(r"\bwe've\s+(\w+)\b", re.IGNORECASE)
_THEYVE_KNOWN = re.compile(r"\bthey've\s+(\w+)\b", re.IGNORECASE)


def _transform_present_for_exp_perfect(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl_ive(m: re.Match) -> str:
        part = m.group(1).lower()
        base = _PARTICIPLE_TO_BASE_FINISH.get(part)
        if base is None:
            base = part[:-2] if part.endswith("ed") else part[:-2] if part.endswith("en") and len(part) > 3 else part
        return f"I {base}"
    def repl_youve(m: re.Match) -> str:
        part = m.group(1).lower()
        base = _PARTICIPLE_TO_BASE_FINISH.get(part)
        if base is None:
            base = part[:-2] if part.endswith("ed") else part[:-2] if part.endswith("en") and len(part) > 3 else part
        return f"you {base}"
    def repl_weve(m: re.Match) -> str:
        part = m.group(1).lower()
        base = _PARTICIPLE_TO_BASE_FINISH.get(part)
        if base is None:
            base = part[:-2] if part.endswith("ed") else part[:-2] if part.endswith("en") and len(part) > 3 else part
        return f"we {base}"
    def repl_theyve(m: re.Match) -> str:
        part = m.group(1).lower()
        base = _PARTICIPLE_TO_BASE_FINISH.get(part)
        if base is None:
            base = part[:-2] if part.endswith("ed") else part[:-2] if part.endswith("en") and len(part) > 3 else part
        return f"they {base}"
    result = _IVE_KNOWN.sub(repl_ive, text)
    result = _YOUVE_KNOWN.sub(repl_youve, result)
    result = _WEVE_KNOWN.sub(repl_weve, result)
    result = _THEYVE_KNOWN.sub(repl_theyve, result)
    return result


def _applicability_present_for_exp_perfect(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for pat in (_IVE_KNOWN, _YOUVE_KNOWN, _WEVE_KNOWN, _THEYVE_KNOWN):
        for m in pat.finditer(text):
            positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": "found I've/you've/we've/they've + participle" if positions else "no exp perfect"}


# --- Batch 9: no-op features → real transforms ---

# --- your_yalls (Paper: your -> y'all's) ---
_YOUR_POSSESSIVE = re.compile(r"\byour\b", re.IGNORECASE)


def _transform_your_yalls(text: str) -> str:
    if not text or not text.strip():
        return text
    return _YOUR_POSSESSIVE.sub("y'all's", text)


def _applicability_your_yalls(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _YOUR_POSSESSIVE.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} your" if positions else "no your",
    }


# --- me_us (Paper: me -> us in object position) ---
_ME_OBJECT = re.compile(r"\bme\b", re.IGNORECASE)


def _transform_me_us(text: str) -> str:
    if not text or not text.strip():
        return text
    return _ME_OBJECT.sub("us", text)


def _applicability_me_us(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _ME_OBJECT.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} me" if positions else "no me",
    }


# --- here_come (Paper: Here comes X -> Here come X; Bring X here -> Take X bring come) ---
_HERE_COMES = re.compile(r"\b(here)\s+comes\b", re.IGNORECASE)
_BRING_X_HERE = re.compile(r"\bBring\s+(.+)\s+here\.?\s*$", re.IGNORECASE)


def _transform_here_come(text: str) -> str:
    if not text or not text.strip():
        return text
    m = _BRING_X_HERE.search(text.strip())
    if m:
        return "Take " + m.group(1) + " bring come."
    def repl(m: re.Match) -> str:
        here = m.group(1)
        return f"{here} come"
    return _HERE_COMES.sub(repl, text)


def _applicability_here_come(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _HERE_COMES.finditer(text)]
    if _BRING_X_HERE.search(text.strip()):
        positions.append((0, len(text.strip())))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} here comes / Bring X here" if positions else "no here come",
    }


# --- plural_interrogative (Paper: Who -> Who-all in questions) ---
_WHO_STANDALONE = re.compile(r"\bWho\s+", re.IGNORECASE)
_WHO_END = re.compile(r"\bWho\s*\??\s*$", re.IGNORECASE)


def _transform_plural_interrogative(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _WHO_STANDALONE.sub("Who-all ", text)
    result = _WHO_END.sub("Who-all?", result)
    return result


def _applicability_plural_interrogative(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _WHO_STANDALONE.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _WHO_END.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} Who" if positions else "no Who in interrogative",
    }


# --- myself_coordinate_subjects (Paper: X and I -> X and myself) ---
_AND_I_WORD = re.compile(r"\band\s+I\b", re.IGNORECASE)


def _transform_myself_coordinate_subjects(text: str) -> str:
    if not text or not text.strip():
        return text
    return _AND_I_WORD.sub("and myself", text)


def _applicability_myself_coordinate_subjects(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _AND_I_WORD.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} and I" if positions else "no and I",
    }


# --- zero_plural_after_quantifier (Paper: five miles -> five mile) ---
_QUANT_PLURAL = re.compile(
    r"\b(two|three|four|five|six|seven|eight|nine|ten|many|several|both|few)\s+(\w+?)s\b",
    re.IGNORECASE,
)
_ZERO_PLURAL_QUANT_EXCLUDE = frozenset("is has was this thus us plus bus focus class".split())


def _transform_zero_plural_after_quantifier(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        quant, stem = m.group(1), m.group(2)
        if not stem or stem.lower() in _ZERO_PLURAL_QUANT_EXCLUDE or len(stem) < 2:
            return m.group(0)
        if stem.lower().endswith("s") or stem.lower().endswith("x") or stem.lower().endswith("z"):
            return m.group(0)
        return f"{quant} {stem}"
    return _QUANT_PLURAL.sub(repl, text)


def _applicability_zero_plural_after_quantifier(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = []
    for m in _QUANT_PLURAL.finditer(text):
        stem = m.group(2).lower()
        if stem and stem not in _ZERO_PLURAL_QUANT_EXCLUDE and len(stem) >= 2 and not (stem.endswith("s") or stem.endswith("x") or stem.endswith("z")):
            positions.append((m.start(), m.end()))
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} quantifier + plural" if positions else "no quantifier + plural",
    }


# --- give_passive (Paper: was scolded by Y -> give Y scold; was/were/been given -> give) ---
_GIVEN_PASSIVE = re.compile(r"\b(was|were|been)\s+given\b", re.IGNORECASE)
_WAS_SCOLDED_BY = re.compile(r"\b(\w+)\s+was\s+scolded\s+by\s+(\w+(?:\s+\w+)*)\s*$", re.IGNORECASE)


def _transform_give_passive(text: str) -> str:
    if not text or not text.strip():
        return text
    m = _WAS_SCOLDED_BY.search(text)
    if m:
        subj, by_obj = m.group(1), m.group(2)
        return f"{subj} give {by_obj} scold."
    return _GIVEN_PASSIVE.sub(r"\1 give", text)


def _applicability_give_passive(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _GIVEN_PASSIVE.finditer(text)]
    m = _WAS_SCOLDED_BY.search(text)
    if m:
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} give passive" if positions else "no give passive",
    }


# --- double_obj_order (Paper: teach it to us -> teach us it) ---
_DOUBLE_OBJ_VERBS = re.compile(
    r"\b(teach|give|send|show|tell)\s+(\S+)\s+to\s+(\S+)\b",
    re.IGNORECASE,
)


def _transform_double_obj_order(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _DOUBLE_OBJ_VERBS.sub(r"\1 \3 \2", text)
    # Contract "She would teach" -> "She'd teach" to match example_var
    result = re.sub(
        r"\b(She|He|I|We|They)\s+would\s+(teach|give|send|show|tell)\b",
        r"\1'd \2",
        result,
        flags=re.IGNORECASE,
    )
    return result


def _applicability_double_obj_order(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _DOUBLE_OBJ_VERBS.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} V NP to NP" if positions else "no double object",
    }


# --- past_tense_leveling (Paper: I saw -> I seen; past -> participle in main verb) ---
# Widen: add more irregular past -> participle for generalization
_PAST_TO_PARTICIPLE: dict[str, str] = {
    "saw": "seen", "went": "gone", "came": "come", "took": "taken", "gave": "given",
    "got": "gotten", "wrote": "written", "spoke": "spoken", "broke": "broken",
    "chose": "chosen", "drove": "driven", "fell": "fallen", "forgot": "forgotten",
    "hid": "hidden", "wore": "worn", "sang": "sung", "did": "done",
    "knew": "known", "threw": "thrown", "drew": "drawn", "grew": "grown",
    "blew": "blown", "flew": "flown", "ate": "eaten", "rode": "ridden",
    "bit": "bitten", "hid": "hidden", "tore": "torn", "wore": "worn",
}
_PAST_LEVELING_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _PAST_TO_PARTICIPLE) + r")\b",
    re.IGNORECASE,
)


def _transform_past_tense_leveling(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        word = m.group(1)
        part = _PAST_TO_PARTICIPLE.get(word.lower())
        if part is None:
            return m.group(0)
        return part if word.islower() else part.capitalize()
    return _PAST_LEVELING_PATTERN.sub(repl, text)


def _applicability_past_tense_leveling(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _PAST_LEVELING_PATTERN.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} past tense verb(s)" if positions else "no past tense leveling",
    }


# --- Batch 10: more no-op features → real transforms ---

# --- benefactive_dative (get one -> get me one) ---
# Widen: get|buy|grab|take|bring + one / one of X / a|the N
_BENEFACTIVE_VERBS = r"(get|buy|grab|take|bring)"
_GET_ONE = re.compile(r"\bget\s+one\b", re.IGNORECASE)
_GET_ONE_OF = re.compile(r"\bget\s+one\s+of\s+\w+\b", re.IGNORECASE)
_GET_X_OF_THOSE = re.compile(r"\bget\s+(\w+)\s+of\s+those\b", re.IGNORECASE)
_GET_A_THE_NOUN = re.compile(r"\bget\s+(a|the)\s+(\w+)\b", re.IGNORECASE)
_BENEFACTIVE_ONE = re.compile(rf"\b{_BENEFACTIVE_VERBS}\s+one\b", re.IGNORECASE)
_BENEFACTIVE_ONE_OF = re.compile(rf"\b{_BENEFACTIVE_VERBS}\s+one\s+of\s+(\w+)\b", re.IGNORECASE)
_BENEFACTIVE_A_THE = re.compile(rf"\b{_BENEFACTIVE_VERBS}\s+(a|the)\s+(\w+)\b", re.IGNORECASE)
_BENEFACTIVE_X_OF_THOSE = re.compile(rf"\b{_BENEFACTIVE_VERBS}\s+(\w+)\s+of\s+those\b", re.IGNORECASE)


def _transform_benefactive_dative(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl_one(m: re.Match) -> str:
        return f"{m.group(1)} me one"
    def repl_one_of(m: re.Match) -> str:
        return f"{m.group(1)} me one of {m.group(2)}"
    def repl_a_the(m: re.Match) -> str:
        return f"{m.group(1)} me {m.group(2)} {m.group(3)}"
    def repl_x_of_those(m: re.Match) -> str:
        return f"{m.group(1)} me {m.group(2)} of those"
    result = _BENEFACTIVE_ONE.sub(repl_one, text)
    result = _BENEFACTIVE_ONE_OF.sub(repl_one_of, result)
    result = _BENEFACTIVE_X_OF_THOSE.sub(repl_x_of_those, result)
    result = _BENEFACTIVE_A_THE.sub(repl_a_the, result)
    return result


def _applicability_benefactive_dative(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _BENEFACTIVE_ONE.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _BENEFACTIVE_ONE_OF.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _BENEFACTIVE_X_OF_THOSE.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _BENEFACTIVE_A_THE.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} get/buy/... one / a|the N" if positions else "no benefactive context",
    }


# --- regularized_reflexives (himself -> hisself) ---
_HIMSELF = re.compile(r"\bhimself\b", re.IGNORECASE)


def _transform_regularized_reflexives(text: str) -> str:
    if not text or not text.strip():
        return text
    return _HIMSELF.sub("hisself", text)


def _applicability_regularized_reflexives(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _HIMSELF.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} himself" if positions else "no himself",
    }


# --- regularized_reflexives_object_pronouns (myself -> meself) ---
_MYSELF_MESELF = re.compile(r"\bmyself\b", re.IGNORECASE)


def _transform_regularized_reflexives_object_pronouns(text: str) -> str:
    if not text or not text.strip():
        return text
    return _MYSELF_MESELF.sub("meself", text)


def _applicability_regularized_reflexives_object_pronouns(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _MYSELF_MESELF.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} myself" if positions else "no myself",
    }


# --- regularized_reflexives_aave (themselves -> theyselves) ---
_THEMSELVES_THEYSELVES = re.compile(r"\bthemselves\b", re.IGNORECASE)


def _transform_regularized_reflexives_aave(text: str) -> str:
    if not text or not text.strip():
        return text
    return _THEMSELVES_THEYSELVES.sub("theyselves", text)


def _applicability_regularized_reflexives_aave(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _THEMSELVES_THEYSELVES.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} themselves" if positions else "no themselves",
    }


# --- reflex_number (ourselves -> ourself, themselves -> themself) ---
_OURSELVES = re.compile(r"\bourselves\b", re.IGNORECASE)
_THEMSELVES_SING = re.compile(r"\bthemselves\b", re.IGNORECASE)


def _transform_reflex_number(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _OURSELVES.sub("ourself", text)
    result = _THEMSELVES_SING.sub("themself", result)
    return result


def _applicability_reflex_number(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _OURSELVES.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _THEMSELVES_SING.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} ourselves/themselves" if positions else "no reflex number",
    }


# --- emphatic_reflex (themselves -> their own self, by themselves -> by their own self) ---
_BY_THEMSELVES = re.compile(r"\bby\s+themselves\b", re.IGNORECASE)
_THEMSELVES_OWN = re.compile(r"\bthemselves\b", re.IGNORECASE)


def _transform_emphatic_reflex(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _BY_THEMSELVES.sub("by their own self", text)
    result = _THEMSELVES_OWN.sub("their own self", result)
    return result


def _applicability_emphatic_reflex(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _THEMSELVES_OWN.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} themselves" if positions else "no emphatic reflex",
    }


# --- absolute_reflex (and he and -> and himself and) ---
_AND_HE_AND = re.compile(r"\band\s+he\s+and\b", re.IGNORECASE)


def _transform_absolute_reflex(text: str) -> str:
    if not text or not text.strip():
        return text
    return _AND_HE_AND.sub("and himself and", text)


def _applicability_absolute_reflex(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _AND_HE_AND.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} and he and" if positions else "no absolute reflex",
    }


# --- reduplicate_interrogative (Who's -> Who-who's, Who -> Who-who) ---
_WHOS_COMING = re.compile(r"\bWho's\b", re.IGNORECASE)
_WHO_VERB = re.compile(r"\bWho\s+(\w+)", re.IGNORECASE)


def _transform_reduplicate_interrogative(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _WHOS_COMING.sub("Who-who's", text)
    result = _WHO_VERB.sub(r"Who-who \1", result)
    return result


def _applicability_reduplicate_interrogative(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _WHOS_COMING.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _WHO_VERB.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} Who/Who's" if positions else "no reduplicate interrogative",
    }


# --- anaphoric_it (than they -> than it) ---
_THAN_THEY = re.compile(r"\bthan\s+they\b", re.IGNORECASE)


def _transform_anaphoric_it(text: str) -> str:
    if not text or not text.strip():
        return text
    return _THAN_THEY.sub("than it", text)


def _applicability_anaphoric_it(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _THAN_THEY.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} than they" if positions else "no anaphoric it",
    }


# --- null_relcl (the N who V -> the N V; remove relativizer who) ---
_WHO_REL_NULL = re.compile(r"\b(the|a|an)\s+(\w+)\s+who\s+", re.IGNORECASE)


def _transform_null_relcl(text: str) -> str:
    if not text or not text.strip():
        return text
    return _WHO_REL_NULL.sub(r"\1 \2 ", text)


def _applicability_null_relcl(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WHO_REL_NULL.finditer(text)]
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} the/a/an N who" if positions else "no null relative",
    }


# --- plural_preposed (birds -> alla bird) ---
# Only match plural nouns in determiner or gerund context to avoid FPs on
# 3rd-person verbs ("sleeps") or subject plurals ("Birds fly").
_PLURAL_PRE_EXCLUDE = frozenset("is has was this thus us plus bus focus class news".split())
_PLURAL_PREPOSED_CTX = re.compile(
    r"\b((?:The|Some|These|Those|Many|All|\w+ing)\s+)(\w+?)s\b",
    re.IGNORECASE,
)


def _transform_plural_preposed(text: str) -> str:
    if not text or not text.strip():
        return text

    def repl(m: re.Match) -> str:
        prefix, stem = m.group(1), m.group(2).lower()
        if not stem or stem in _PLURAL_PRE_EXCLUDE or len(stem) < 2:
            return m.group(0)
        if stem.endswith("s") or stem.endswith("x") or stem.endswith("z"):
            return m.group(0)
        return f"{prefix}alla {m.group(2)}"
    return _PLURAL_PREPOSED_CTX.sub(repl, text)


def _applicability_plural_preposed(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = []
    for m in _PLURAL_PREPOSED_CTX.finditer(text):
        stem = m.group(2).lower()
        if stem and stem not in _PLURAL_PRE_EXCLUDE and len(stem) >= 2 and not (stem.endswith("s") or stem.endswith("x") or stem.endswith("z")):
            positions.append((m.start(2), m.end(2)))
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} plural noun(s) in determiner/gerund context" if positions else "no plural preposed",
    }


# --- plural_postposed (The Ns -> Da N dem) ---
_THE_PLURAL = re.compile(r"\bThe\s+(\w+?)s\b", re.IGNORECASE)
_PLURAL_POST_EXCLUDE = frozenset("is has us this thus plus bus focus class".split())


def _transform_plural_postposed(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        stem = m.group(1).lower()
        if stem in _PLURAL_POST_EXCLUDE or len(stem) < 2:
            return m.group(0)
        return f"Da {m.group(1)} dem"
    return _THE_PLURAL.sub(repl, text)


def _applicability_plural_postposed(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = []
    for m in _THE_PLURAL.finditer(text):
        if m.group(1).lower() not in _PLURAL_POST_EXCLUDE and len(m.group(1)) >= 2:
            positions.append((m.start(), m.end()))
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} The Ns" if positions else "no plural postposed",
    }


# --- plural_to_singular_human (people -> person, girls -> girl) ---
_PEOPLE = re.compile(r"\bpeople\b", re.IGNORECASE)
_GIRLS = re.compile(r"\bgirls\b", re.IGNORECASE)


def _transform_plural_to_singular_human(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _PEOPLE.sub("person", text)
    result = _GIRLS.sub("girl", result)
    return result


def _applicability_plural_to_singular_human(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _PEOPLE.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _GIRLS.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} people/girls" if positions else "no plural_to_singular_human",
    }


# --- relativizer_doubling (who -> that which in relative context) ---
_WHO_HAD = re.compile(r"\bwho\s+had\s+", re.IGNORECASE)
_WHO_VERB_REL = re.compile(r"\bwho\s+(\w+)\s+", re.IGNORECASE)


def _transform_relativizer_doubling(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _WHO_HAD.sub("that which had ", text)
    result = _WHO_VERB_REL.sub(r"that which \1 ", result)
    # Match example_var: "before" at end -> "befo'"
    result = re.sub(r"\bbefore\s*$", "befo'", result, flags=re.IGNORECASE)
    return result


def _applicability_relativizer_doubling(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _WHO_HAD.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _WHO_VERB_REL.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} who + verb" if positions else "no relativizer doubling",
    }


# --- it_dobj (explained to -> explained it to) ---
_EXPLAINED_TO = re.compile(r"\bexplained\s+to\b", re.IGNORECASE)
_SAID_TO = re.compile(r"\bsaid\s+to\b", re.IGNORECASE)


def _transform_it_dobj(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _EXPLAINED_TO.sub("explained it to", text)
    result = _SAID_TO.sub("said it to", result)
    return result


def _applicability_it_dobj(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _EXPLAINED_TO.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _SAID_TO.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} explained/said to" if positions else "no it dobj",
    }


# --- no_gender_distinction (she -> he, her -> him; IndE "He for she") ---
_SHE_SUBJECT = re.compile(r"\b(she)\b", re.IGNORECASE)
_HER_OBJ = re.compile(r"\b(her)\b", re.IGNORECASE)


def _transform_no_gender_distinction(text: str) -> str:
    if not text or not text.strip():
        return text
    def he_cap(m: re.Match) -> str:
        return "He" if m.group(1)[0].isupper() else "he"
    def him_cap(m: re.Match) -> str:
        return "Him" if m.group(1)[0].isupper() else "him"
    result = _SHE_SUBJECT.sub(he_cap, text)
    result = _HER_OBJ.sub(him_cap, result)
    return result


def _applicability_no_gender_distinction(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _SHE_SUBJECT.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _HER_OBJ.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {
        "applicable": len(positions) > 0,
        "match_count": len(positions),
        "match_positions": positions,
        "reason": f"found {len(positions)} he/she/him/to her" if positions else "no gender distinction",
    }


# --- Batch 11: final 26 no-op features → real transforms ---

# --- it_is_referential (It is X -> Is X; drop referential it) ---
_IT_IS_REF = re.compile(r"\bIt is\b", re.IGNORECASE)


def _transform_it_is_referential(text: str) -> str:
    if not text or not text.strip():
        return text
    return _IT_IS_REF.sub("Is", text)


def _applicability_it_is_referential(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _IT_IS_REF.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} It is" if positions else "no It is"}


# --- it_is_non_referential (it's time -> is time) ---
_ITS_NONREF = re.compile(r"\bit's\b", re.IGNORECASE)


def _transform_it_is_non_referential(text: str) -> str:
    if not text or not text.strip():
        return text
    return _ITS_NONREF.sub("is", text)


def _applicability_it_is_non_referential(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _ITS_NONREF.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} it's" if positions else "no it's"}


# --- em_subj_pronoun (she -> 'em as subject) ---
_SHE_EM = re.compile(r"\bshe\b", re.IGNORECASE)


def _transform_em_subj_pronoun(text: str) -> str:
    if not text or not text.strip():
        return text
    return _SHE_EM.sub("'em", text)


def _applicability_em_subj_pronoun(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _SHE_EM.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} she" if positions else "no she"}


# --- em_obj_pronoun (it -> 'im as object) ---
_IT_IM = re.compile(r"\bit\b", re.IGNORECASE)


def _transform_em_obj_pronoun(text: str) -> str:
    if not text or not text.strip():
        return text
    return _IT_IM.sub("'im", text)


def _applicability_em_obj_pronoun(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _IT_IM.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} it" if positions else "no it"}


# --- non_coordinated_subj_obj (with us -> with we) ---
_WITH_US = re.compile(r"\bwith us\b", re.IGNORECASE)


def _transform_non_coordinated_subj_obj(text: str) -> str:
    if not text or not text.strip():
        return text
    return _WITH_US.sub("with we", text)


def _applicability_non_coordinated_subj_obj(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WITH_US.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} with us" if positions else "no with us"}


# --- non_coordinated_obj_subj (They -> Them as subject) ---
_THEY_THEM = re.compile(r"\bThey\b")
_they_them = re.compile(r"\bthey\b")


def _transform_non_coordinated_obj_subj(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _THEY_THEM.sub("Them", text)
    result = _they_them.sub("them", result)
    return result


def _applicability_non_coordinated_obj_subj(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _THEY_THEM.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _they_them.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} they" if positions else "no they"}


# --- existential_possessives (I have a N -> N is there) ---
_I_HAVE_A = re.compile(r"\bI have a (\w+)\b", re.IGNORECASE)


def _transform_existential_possessives(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        n = m.group(1)
        return f"{n.capitalize()} is there"
    return _I_HAVE_A.sub(repl, text)


def _applicability_existential_possessives(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _I_HAVE_A.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} I have a N" if positions else "no I have a N"}


# --- possessives_for_post (X's Y -> the Y for X) ---
# Restrict possessor to (optional my/your/... + word) or single word so we don't match "This is my mother's"
_POSS_POST = re.compile(r"\b((?:my|your|his|her|our|their)\s+\w+|\w+)'s (\w+)\b", re.IGNORECASE)


def _transform_possessives_for_post(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        return f"the {m.group(2)} for {m.group(1)}"
    return _POSS_POST.sub(repl, text)


def _applicability_possessives_for_post(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _POSS_POST.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} X's Y" if positions else "no possessive"}


# --- possessives_for_pre (X's Y -> for X Y); also drop "ago" in "Long time ago" ---
_POSS_PRE = re.compile(r"\b((?:my|your|his|her|our|their)\s+\w+|\w+)'s (\w+)\b", re.IGNORECASE)


def _transform_possessives_for_pre(text: str) -> str:
    if not text or not text.strip():
        return text
    result = re.sub(r"\bLong time ago\b", "Long time", text, flags=re.IGNORECASE)
    def repl(m: re.Match) -> str:
        return f"for {m.group(1)} {m.group(2)}"
    return _POSS_PRE.sub(repl, result)


def _applicability_possessives_for_pre(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _POSS_PRE.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} X's Y" if positions else "no possessive"}


# --- possessives_belong (the X's Y -> X belong Y) ---
_THE_POSS_BELONG = re.compile(r"\bthe (\w+)'s (\w+)\b", re.IGNORECASE)


def _transform_possessives_belong(text: str) -> str:
    if not text or not text.strip():
        return text
    return _THE_POSS_BELONG.sub(r"\1 belong \2", text)


def _applicability_possessives_belong(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _THE_POSS_BELONG.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} the X's Y" if positions else "no the X's Y"}


# --- mass_noun_plurals (furniture -> furnitures, etc.) ---
_MASS_NOUNS: dict[str, str] = {
    "furniture": "furnitures", "machinery": "machineries", "equipment": "equipments",
    "evidence": "evidences", "luggage": "luggages", "advice": "advices", "mail": "mails",
    "staff": "staffs", "information": "informations", "news": "newses",
}
_MASS_PATTERN = re.compile(r"\b(" + "|".join(re.escape(k) for k in _MASS_NOUNS) + r")\b", re.IGNORECASE)


def _transform_mass_noun_plurals(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        w = m.group(1)
        val = _MASS_NOUNS.get(w.lower(), w)
        return val.capitalize() if w[0].isupper() else val
    return _MASS_PATTERN.sub(repl, text)


def _applicability_mass_noun_plurals(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _MASS_PATTERN.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} mass noun(s)" if positions else "no mass noun"}


# --- that_resultative_past_participle (that broke down -> broken down) ---
_THAT_BROKE_DOWN = re.compile(r"\bthat broke down\b", re.IGNORECASE)
_THAT_BROKE = re.compile(r"\bthat broke\b", re.IGNORECASE)


def _transform_that_resultative_past_participle(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _THAT_BROKE_DOWN.sub("broken down", text)
    result = _THAT_BROKE.sub("broken", result)
    return result


def _applicability_that_resultative_past_participle(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _THAT_BROKE_DOWN.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _THAT_BROKE.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} that broke" if positions else "no that broke"}


# --- medial_object_perfect (has written a letter -> has a letter written) ---
_HAS_PARTICIPLE_A = re.compile(r"\b(has|have) (\w+ed|\w+en) (a|the) (\w+)\b", re.IGNORECASE)


def _transform_medial_object_perfect(text: str) -> str:
    if not text or not text.strip():
        return text
    return _HAS_PARTICIPLE_A.sub(r"\1 \3 \4 \2", text)


def _applicability_medial_object_perfect(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _HAS_PARTICIPLE_A.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} has/have Ved a/the N" if positions else "no medial object perfect"}


# --- serial_verb_give (bought X for you -> buy X give you) ---
_BOUGHT_FOR_YOU = re.compile(r"\bbought (\w+) for (you|them|her|him)\b", re.IGNORECASE)


def _transform_serial_verb_give(text: str) -> str:
    if not text or not text.strip():
        return text
    return _BOUGHT_FOR_YOU.sub(r"buy \1 give \2", text)


def _applicability_serial_verb_give(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _BOUGHT_FOR_YOU.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} bought X for" if positions else "no serial give"}


# --- serial_verb_go (sends us to X -> send us go X) ---
_SENDS_TO = re.compile(r"\b(send|sends) (us|me) to (\w+)\b", re.IGNORECASE)


def _transform_serial_verb_go(text: str) -> str:
    if not text or not text.strip():
        return text
    return _SENDS_TO.sub(r"send \2 go \3", text)


def _applicability_serial_verb_go(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _SENDS_TO.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} send(s) us/me to" if positions else "no serial go"}


# --- transitive_suffix (see the fish -> see 'im fish) ---
# Widen: more verbs + the + noun
_SEE_THE = re.compile(
    r"\b(see|catch|get|watch|find|spot|grab|like|want|love|need|know|take|make|give|bring|buy|have)\s+the\s+(\w+)\b",
    re.IGNORECASE,
)


def _transform_transitive_suffix(text: str) -> str:
    if not text or not text.strip():
        return text
    return _SEE_THE.sub(r"\1 'im \2", text)


def _applicability_transitive_suffix(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _SEE_THE.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} V the N" if positions else "no transitive suffix"}


# --- shadow_pronouns (which I painted -> which I painted it) ---
_WHICH_I_VERB = re.compile(r"\bwhich I (\w+)\b", re.IGNORECASE)


def _transform_shadow_pronouns(text: str) -> str:
    if not text or not text.strip():
        return text
    return _WHICH_I_VERB.sub(r"which I \1 it", text)


def _applicability_shadow_pronouns(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WHICH_I_VERB.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} which I V" if positions else "no shadow pronoun"}


# --- one_relativizer (that John buys -> John buy one) ---
_THAT_NP_VS = re.compile(r"\bthat (\w+) (\w+)s\b", re.IGNORECASE)


def _transform_one_relativizer(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _THAT_NP_VS.sub(r"\1 \2 one", text)
    # "John buy one is always" -> "John buy one always" to match example_var
    result = re.sub(r"\bone is\s+", "one ", result, flags=re.IGNORECASE)
    return result


def _applicability_one_relativizer(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _THAT_NP_VS.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} that N Vs" if positions else "no one relativizer"}


# --- analytic_whose_relativizer (whose wife -> that his wife) ---
_WHOSE_N = re.compile(r"\bwhose (\w+)\b", re.IGNORECASE)


def _transform_analytic_whose_relativizer(text: str) -> str:
    if not text or not text.strip():
        return text
    return _WHOSE_N.sub(r"that his \1", text)


def _applicability_analytic_whose_relativizer(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WHOSE_N.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} whose N" if positions else "no whose"}


# --- correlative_constructions (The ones I made are the good ones -> The one I made, that one is good) ---
_THE_ONES = re.compile(r"\bThe ones\b")
_ARE_THE_GOOD_ONES = re.compile(r"\bare the good ones\b", re.IGNORECASE)


def _transform_correlative_constructions(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _THE_ONES.sub("The one", text)
    result = _ARE_THE_GOOD_ONES.sub(", that one is good", result)
    result = re.sub(r"\s+,", ",", result)  # no space before comma to match example_var
    return result


def _applicability_correlative_constructions(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions: list[tuple[int, int]] = []
    for m in _THE_ONES.finditer(text):
        positions.append((m.start(), m.end()))
    for m in _ARE_THE_GOOD_ONES.finditer(text):
        positions.append((m.start(), m.end()))
    positions.sort(key=lambda p: p[0])
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} The ones / are the good ones" if positions else "no correlative"}


# --- doubly_filled_comp (Who ate what? -> What who has eaten?) ---
_WHO_ATE_WHAT = re.compile(r"\bWho ate what\s*\??\s*$", re.IGNORECASE)


def _transform_doubly_filled_comp(text: str) -> str:
    if not text or not text.strip():
        return text
    return _WHO_ATE_WHAT.sub("What who has eaten?", text)


def _applicability_doubly_filled_comp(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WHO_ATE_WHAT.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} Who ate what" if positions else "no doubly filled"}


# --- inverted_indirect_question (what you are -> what are you) ---
_WHAT_YOU_ARE = re.compile(r"\bwhat you (are|were|was|is|do|did|have|had)\b", re.IGNORECASE)


def _transform_inverted_indirect_question(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        return f"what {m.group(1)} you"
    return _WHAT_YOU_ARE.sub(repl, text)


def _applicability_inverted_indirect_question(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _WHAT_YOU_ARE.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} what you V" if positions else "no inverted indirect"}


# --- clefting (NP are looking for X -> It's looking for X NP are) ---
_CLEFT_PATTERN = re.compile(r"\b(.+?) are (looking|going|waiting) for (.+?)\.", re.IGNORECASE)


def _transform_clefting(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        subj, verb, obj = m.group(1).strip(), m.group(2), m.group(3).strip()
        # Lowercase moved subject to match example_var (a lot not A lot)
        subj_lower = subj[0].lower() + subj[1:] if len(subj) > 1 else subj.lower()
        return f"It's {verb} for {obj} {subj_lower} are."
    return _CLEFT_PATTERN.sub(repl, text)


def _applicability_clefting(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _CLEFT_PATTERN.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} NP are Ving for" if positions else "no cleft"}


# --- fronting_pobj (I drive to town X -> To town X I drive) ---
_FRONT_POBJ = re.compile(r"\bI (drive|go|walk) (to \w+) (.+?)\.", re.IGNORECASE)


def _transform_fronting_pobj(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        pp, rest, v = m.group(2), m.group(3), m.group(1)
        return f"{pp.capitalize()} {rest} I {v}."
    return _FRONT_POBJ.sub(repl, text)


def _applicability_fronting_pobj(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _FRONT_POBJ.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} I drive/go/walk to" if positions else "no fronting"}


# --- superlative_before_matrix_head (The thing I like most -> The most thing I like) ---
# Widen: the N I (like|love|want|know|enjoy) most
# Widen: more matrix verbs (see, find, prefer, think, remember)
_THING_I_LIKE_MOST = re.compile(
    r"\bthe\s+(\w+)\s+I\s+(like|love|want|know|enjoy|see|find|prefer|think|remember|understand)\s+most\b",
    re.IGNORECASE,
)


def _transform_superlative_before_matrix_head(text: str) -> str:
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        n, v = m.group(1), m.group(2)
        return f"The most {n} I {v}"
    return _THING_I_LIKE_MOST.sub(repl, text)


def _applicability_superlative_before_matrix_head(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _THING_I_LIKE_MOST.finditer(text)]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} the N I V most" if positions else "no superlative"}


# --- chaining_main_verbs (If you stay longer, they have to charge more -> Stay longer, they have to over-charge) ---
_HAVE_TO_V_MORE = re.compile(r"\bhave to (\w+) more\b", re.IGNORECASE)
_IF_YOU_START = re.compile(r"^\s*If you\s+", re.IGNORECASE)


def _transform_chaining_main_verbs(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _IF_YOU_START.sub("", text.strip())
    if result and result[0].islower():
        result = result[0].upper() + result[1:]
    def repl(m: re.Match) -> str:
        return f"have to over-{m.group(1)}"
    result = _HAVE_TO_V_MORE.sub(repl, result)
    return result


def _applicability_chaining_main_verbs(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty string"}
    positions = [(m.start(), m.end()) for m in _HAVE_TO_V_MORE.finditer(text)]
    if _IF_YOU_START.match(text.strip()):
        positions.append((0, 7))
    positions.sort(key=lambda p: p[0])
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} have to V more / If you" if positions else "no chaining"}


# --- Extra 1: got (present-tense have/has -> got) ---
_HAVE_GOT_OBJ = re.compile(r"\b(I|you|we|they)\s+have\s+(?!(?:to|been|got)\b)(\w+)", re.IGNORECASE)
_HAS_GOT_OBJ = re.compile(r"\b(he|she|it)\s+has\s+(?!(?:to|been|got)\b)(\w+)", re.IGNORECASE)


def _transform_got(text: str) -> str:
    if not text or not text.strip():
        return text
    result = _HAVE_GOT_OBJ.sub(r"\1 got \2", text)
    result = _HAS_GOT_OBJ.sub(r"\1 got \2", result)
    return result


def _applicability_got(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty"}
    positions = [(m.start(), m.end()) for m in _HAVE_GOT_OBJ.finditer(text)]
    positions.extend((m.start(), m.end()) for m in _HAS_GOT_OBJ.finditer(text))
    positions.sort(key=lambda p: p[0])
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} have/has + obj" if positions else "no have/has"}


# --- Extra 2: ass_pronoun (intensifier / pronoun camouflage) ---
_IS_ARE_ADJ = re.compile(r"\b(is|are|was|were)\s+(\w+)(\s|$|\.|,)", re.IGNORECASE)


def _transform_ass_pronoun(text: str) -> str:
    """Add intensifier 'ass' before adjective in is/are/was/were + ADJ (e.g. 'is fast' -> 'is ass fast')."""
    if not text or not text.strip():
        return text
    def repl(m: re.Match) -> str:
        verb, adj, tail = m.group(1), m.group(2), m.group(3)
        if adj.lower() in ("a", "an", "the", "some", "no", "not", "very", "too", "ass"):
            return m.group(0)
        return f"{verb} ass {adj}{tail}"
    return _IS_ARE_ADJ.sub(repl, text)


def _applicability_ass_pronoun(text: str) -> dict:
    if not text:
        return {"applicable": False, "match_count": 0, "match_positions": [], "reason": "empty"}
    positions = [(m.start(), m.end()) for m in _IS_ARE_ADJ.finditer(text) if m.group(2).lower() not in ("a", "an", "the", "some", "no", "not", "very", "too", "ass")]
    return {"applicable": len(positions) > 0, "match_count": len(positions), "match_positions": positions, "reason": f"found {len(positions)} be + adj" if positions else "no be + adj"}


# --- No-op for features without a real transform (so all 200+ show in app with applicability) ---

def _transform_noop(text: str) -> str:
    """Identity transform for features not yet implemented (paper feature placeholder)."""
    return text


def _applicability_noop(text: str) -> dict:
    """Applicability for unimplemented features: never applicable."""
    return {
        "applicable": False,
        "match_count": 0,
        "match_positions": [],
        "reason": "transform not yet implemented (paper feature)",
    }


# --- Registration ---

def _register_transform(
    feature_id: str,
    transform: Callable[[str], str],
    applicability_check: Callable[[str], dict],
) -> None:
    f = get_feature(feature_id)
    register(replace(f, transform=transform, applicability_check=applicability_check))


def _register_all_transforms() -> None:
    try:
        load_features_from_json()
    except FileNotFoundError:
        pass
    # Real transforms: paper feature ids only (Ziems 189)
    pairs = [
        # Paper ids (same transform shared where applicable)
        ("negative_concord", _transform_negative_concord, _applicability_negative_concord),
        ("dont", _transform_dont, _applicability_dont),
        ("never_negator", _transform_never_negator, _applicability_never_negator),
        ("completive_done", _transform_completive_done, _applicability_completive_done),
        ("existential_it", _transform_existential_it, _applicability_existential_it),
        ("existential_there", _transform_existential_there, _applicability_existential_there_feature),
        ("conditional_were_was", _transform_conditional_were_was, _applicability_conditional_were_was),
        ("degree_adj_for_adv", _transform_degree_adj_for_adv, _applicability_degree_adj_for_adv),
        ("flat_adj_for_adv", _transform_flat_adj_for_adv, _applicability_flat_adj_for_adv),
        ("drop_copula_be_NP", _transform_copula_deletion, _applicability_copula_deletion),
        ("drop_copula_be_AP", _transform_copula_deletion, _applicability_copula_deletion),
        ("drop_copula_be_locative", _transform_copula_deletion, _applicability_copula_deletion),
        ("those_them", _transform_them_as_demonstrative, _applicability_them_as_demonstrative),
        ("were_was", _transform_was_leveling, _applicability_was_leveling),
        ("null_genitive", _transform_possessive_s_absence, _applicability_possessive_s_absence),
        ("yall", _transform_yall, _applicability_yall),
        ("finna_future", _transform_finna_future, _applicability_fixin_to),
        ("fixin_future", _transform_fixin_to, _applicability_fixin_to),
        ("future_sub_gon", _transform_future_sub_gon, _applicability_future_sub_gon),
        ("volition_changes", _transform_volition_changes, _applicability_volition_changes),
        ("drop_aux_have", _transform_drop_auxiliary, _applicability_drop_auxiliary),
        ("null_prepositions", _transform_drop_prepositions, _applicability_drop_prepositions),
        ("remove_det_definite", _transform_drop_articles, _applicability_drop_articles),
        ("remove_det_indefinite", _transform_drop_articles, _applicability_drop_articles),
        ("aint_be", _transform_aint_negation, _applicability_aint_negation),
        ("aint_have", _transform_aint_negation, _applicability_aint_negation),
        ("aint_before_main", _transform_aint_negation, _applicability_aint_negation),
        # New real transforms for paper features
        ("double_modals", _transform_double_modals, _applicability_double_modals),
        ("who_what", _transform_who_what, _applicability_who_what),
        ("got_gotten", _transform_got_gotten, _applicability_got_gotten),
        ("drop_aux_be_gonna", _transform_drop_aux_be_gonna, _applicability_drop_aux_be_gonna),
        ("wasnt_werent", _transform_wasnt_werent, _applicability_wasnt_werent),
        ("regularized_past_tense", _transform_regularized_past_tense, _applicability_regularized_past_tense),
        ("participle_past_tense", _transform_participle_past_tense, _applicability_participle_past_tense),
        ("uninflect", _transform_uninflect, _applicability_uninflect),
        ("preposition_chopping", _transform_preposition_chopping, _applicability_preposition_chopping),
        ("what_comparative", _transform_what_comparative, _applicability_what_comparative),
        ("drop_inf_to", _transform_drop_inf_to, _applicability_drop_inf_to),
        # Additional paper features (batch 2)
        ("definite_for_indefinite_articles", _transform_definite_for_indefinite_articles, _applicability_definite_for_indefinite_articles),
        ("indefinite_for_definite_articles", _transform_indefinite_for_definite_articles, _applicability_indefinite_for_definite_articles),
        ("too_sub", _transform_too_sub, _applicability_too_sub),
        ("is_am_1s", _transform_is_am_1s, _applicability_is_am_1s),
        ("present_modals", _transform_present_modals, _applicability_present_modals),
        ("nomo_existential", _transform_nomo_existential, _applicability_nomo_existential),
        ("no_preverbal_negator", _transform_no_preverbal_negator, _applicability_no_preverbal_negator),
        ("not_preverbal_negator", _transform_not_preverbal_negator, _applicability_not_preverbal_negator),
        ("bare_past_tense", _transform_bare_past_tense, _applicability_bare_past_tense),
        ("a_ing", _transform_a_ing, _applicability_a_ing),
        ("double_determiners", _transform_double_determiners, _applicability_double_determiners),
        ("invariant_tag_non_concord", _transform_invariant_tag_non_concord, _applicability_invariant_tag_non_concord),
        ("invariant_tag_amnt", _transform_invariant_tag_amnt, _applicability_invariant_tag_amnt),
        ("invariant_tag_can_or_not", _transform_invariant_tag_can_or_not, _applicability_invariant_tag_can_or_not),
        ("invariant_tag_fronted_isnt", _transform_invariant_tag_fronted_isnt, _applicability_invariant_tag_fronted_isnt),
        # Batch 3
        ("will_would", _transform_will_would, _applicability_will_would),
        ("if_would", _transform_if_would, _applicability_if_would),
        ("standing_stood", _transform_standing_stood, _applicability_standing_stood),
        ("indefinite_for_zero", _transform_indefinite_for_zero, _applicability_indefinite_for_zero),
        ("more_much", _transform_more_much, _applicability_more_much),
        ("regularized_plurals", _transform_regularized_plurals, _applicability_regularized_plurals),
        ("zero_plural", _transform_zero_plural, _applicability_zero_plural),
        ("simple_past_for_present_perfect", _transform_simple_past_for_present_perfect, _applicability_simple_past_for_present_perfect),
        ("present_perfect_for_past", _transform_present_perfect_for_past, _applicability_present_perfect_for_past),
        ("bare_perfect", _transform_bare_perfect, _applicability_bare_perfect),
        ("past_for_past_participle", _transform_past_for_past_participle, _applicability_past_for_past_participle),
        ("double_past", _transform_double_past, _applicability_double_past),
        ("generalized_third_person_s", _transform_generalized_third_person_s, _applicability_generalized_third_person_s),
        ("drop_aux_be_progressive", _transform_drop_aux_be_progressive, _applicability_drop_aux_be_progressive),
        # Batch 4
        ("demonstrative_no_number", _transform_demonstrative_no_number, _applicability_demonstrative_no_number),
        ("double_comparative", _transform_double_comparative, _applicability_double_comparative),
        ("double_superlative", _transform_double_superlative, _applicability_double_superlative),
        ("comparative_as_to", _transform_comparative_as_to, _applicability_comparative_as_to),
        ("comparative_than", _transform_comparative_than, _applicability_comparative_than),
        ("comparative_more_and", _transform_comparative_more_and, _applicability_comparative_more_and),
        ("synthetic_superlative", _transform_synthetic_superlative, _applicability_synthetic_superlative),
        ("analytic_superlative", _transform_analytic_superlative, _applicability_analytic_superlative),
        ("progressives", _transform_progressives, _applicability_progressives),
        ("do_tense_marker", _transform_do_tense_marker, _applicability_do_tense_marker),
        ("come_future", _transform_come_future, _applicability_come_future),
        ("existential_got", _transform_existential_got, _applicability_existential_got),
        ("existential_you_have", _transform_existential_you_have, _applicability_existential_you_have),
        ("drop_aux_wh", _transform_drop_aux_wh, _applicability_drop_aux_wh),
        ("drop_aux_yn", _transform_drop_aux_yn, _applicability_drop_aux_yn),
        ("quotative_like", _transform_quotative_like, _applicability_quotative_like),
        # Batch 5
        ("demonstrative_for_definite_articles", _transform_demonstrative_for_definite_articles, _applicability_demonstrative_for_definite_articles),
        ("clause_final_though_but", _transform_clause_final_though_but, _applicability_clause_final_though_but),
        ("zero_degree", _transform_zero_degree, _applicability_zero_degree),
        ("who_which", _transform_who_which, _applicability_who_which),
        ("who_as", _transform_who_as, _applicability_who_as),
        ("who_at", _transform_who_at, _applicability_who_at),
        ("completive_have_done", _transform_completive_have_done, _applicability_completive_have_done),
        ("completive_finish", _transform_completive_finish, _applicability_completive_finish),
        ("present_for_neutral_future", _transform_present_for_neutral_future, _applicability_present_for_neutral_future),
        ("past_been", _transform_past_been, _applicability_past_been),
        ("a_participle", _transform_a_participle, _applicability_a_participle),
        ("verbal_ing_suffix", _transform_verbal_ing_suffix, _applicability_verbal_ing_suffix),
        ("indef_one", _transform_indef_one, _applicability_indef_one),
        ("definite_abstract", _transform_definite_abstract, _applicability_definite_abstract),
        ("acomp_focusing_like", _transform_acomp_focusing_like, _applicability_acomp_focusing_like),
        # Batch 6
        ("pleonastic_that", _transform_pleonastic_that, _applicability_pleonastic_that),
        ("my_i", _transform_my_i, _applicability_my_i),
        ("our_we", _transform_our_we, _applicability_our_we),
        ("his_he", _transform_his_he, _applicability_his_he),
        ("their_they", _transform_their_they, _applicability_their_they),
        ("your_you", _transform_your_you, _applicability_your_you),
        ("object_pronoun_drop", _transform_object_pronoun_drop, _applicability_object_pronoun_drop),
        ("say_complementizer", _transform_say_complementizer, _applicability_say_complementizer),
        ("for_to", _transform_for_to, _applicability_for_to),
        ("bare_ccomp", _transform_bare_ccomp, _applicability_bare_ccomp),
        ("negative_inversion", _transform_negative_inversion, _applicability_negative_inversion),
        ("clause_final_really_but", _transform_clause_final_really_but, _applicability_clause_final_really_but),
        ("me_coordinate_subjects", _transform_me_coordinate_subjects, _applicability_me_coordinate_subjects),
        ("subord_conjunction_doubling", _transform_subord_conjunction_doubling, _applicability_subord_conjunction_doubling),
        ("corr_conjunction_doubling", _transform_corr_conjunction_doubling, _applicability_corr_conjunction_doubling),
        # Batch 7
        ("referential_thing", _transform_referential_thing, _applicability_referential_thing),
        ("you_ye", _transform_you_ye, _applicability_you_ye),
        ("be_perfect", _transform_be_perfect, _applicability_be_perfect),
        ("irrealis_be_done", _transform_irrealis_be_done, _applicability_irrealis_be_done),
        ("present_perfect_ever", _transform_present_perfect_ever, _applicability_present_perfect_ever),
        ("perfect_already", _transform_perfect_already, _applicability_perfect_already),
        ("perfect_slam", _transform_perfect_slam, _applicability_perfect_slam),
        ("relativizer_where", _transform_relativizer_where, _applicability_relativizer_where),
        ("to_infinitive", _transform_to_infinitive, _applicability_to_infinitive),
        ("after_perfect", _transform_after_perfect, _applicability_after_perfect),
        ("for_complementizer", _transform_for_complementizer, _applicability_for_complementizer),
        ("for_to_purpose", _transform_for_to_pupose, _applicability_for_to_pupose),
        # Batch 8
        ("she_inanimate_objects", _transform_she_inanimate_objects, _applicability_she_inanimate_objects),
        ("he_inanimate_objects", _transform_he_inanimate_objects, _applicability_he_inanimate_objects),
        ("my_me", _transform_my_me, _applicability_my_me),
        ("our_us", _transform_our_us, _applicability_our_us),
        ("his_him", _transform_his_him, _applicability_his_him),
        ("their_them", _transform_their_them, _applicability_their_them),
        ("linking_relcl", _transform_linking_relcl, _applicability_linking_relcl),
        ("reduced_relative", _transform_reduced_relative, _applicability_reduced_relative),
        ("that_infinitival_subclause", _transform_that_infinitival_subclause, _applicability_that_infinitival_subclause),
        ("proximal_distal_demonstratives", _transform_proximal_distal_demonstratives, _applicability_proximal_distal_demonstratives),
        ("adj_postfix", _transform_adj_postfix, _applicability_adj_postfix),
        ("present_for_exp_perfect", _transform_present_for_exp_perfect, _applicability_present_for_exp_perfect),
        # Batch 9: new real transforms
        ("your_yalls", _transform_your_yalls, _applicability_your_yalls),
        ("me_us", _transform_me_us, _applicability_me_us),
        ("here_come", _transform_here_come, _applicability_here_come),
        ("plural_interrogative", _transform_plural_interrogative, _applicability_plural_interrogative),
        ("myself_coordinate_subjects", _transform_myself_coordinate_subjects, _applicability_myself_coordinate_subjects),
        ("zero_plural_after_quantifier", _transform_zero_plural_after_quantifier, _applicability_zero_plural_after_quantifier),
        ("give_passive", _transform_give_passive, _applicability_give_passive),
        ("double_obj_order", _transform_double_obj_order, _applicability_double_obj_order),
        ("null_referential_pronouns", _transform_drop_subject_pronoun, _applicability_drop_subject_pronoun),
        # Batch 10
        ("benefactive_dative", _transform_benefactive_dative, _applicability_benefactive_dative),
        ("regularized_reflexives", _transform_regularized_reflexives, _applicability_regularized_reflexives),
        ("regularized_reflexives_object_pronouns", _transform_regularized_reflexives_object_pronouns, _applicability_regularized_reflexives_object_pronouns),
        ("regularized_reflexives_aave", _transform_regularized_reflexives_aave, _applicability_regularized_reflexives_aave),
        ("reflex_number", _transform_reflex_number, _applicability_reflex_number),
        ("emphatic_reflex", _transform_emphatic_reflex, _applicability_emphatic_reflex),
        ("absolute_reflex", _transform_absolute_reflex, _applicability_absolute_reflex),
        ("reduplicate_interrogative", _transform_reduplicate_interrogative, _applicability_reduplicate_interrogative),
        ("anaphoric_it", _transform_anaphoric_it, _applicability_anaphoric_it),
        ("null_relcl", _transform_null_relcl, _applicability_null_relcl),
        ("plural_to_singular_human", _transform_plural_to_singular_human, _applicability_plural_to_singular_human),
        ("relativizer_doubling", _transform_relativizer_doubling, _applicability_relativizer_doubling),
        ("it_dobj", _transform_it_dobj, _applicability_it_dobj),
        ("no_gender_distinction", _transform_no_gender_distinction, _applicability_no_gender_distinction),
        ("nasal_possessive_pron", _transform_nasal_possessive_pron, _applicability_nasal_possessive_pron),
        # Extra (no eWAVE ID)
        ("got", _transform_got, _applicability_got),
        ("ass_pronoun", _transform_ass_pronoun, _applicability_ass_pronoun),
        # Batch 11: final 24
        ("it_is_referential", _transform_it_is_referential, _applicability_it_is_referential),
        ("it_is_non_referential", _transform_it_is_non_referential, _applicability_it_is_non_referential),
        ("em_subj_pronoun", _transform_em_subj_pronoun, _applicability_em_subj_pronoun),
        ("em_obj_pronoun", _transform_em_obj_pronoun, _applicability_em_obj_pronoun),
        ("non_coordinated_subj_obj", _transform_non_coordinated_subj_obj, _applicability_non_coordinated_subj_obj),
        ("non_coordinated_obj_subj", _transform_non_coordinated_obj_subj, _applicability_non_coordinated_obj_subj),
        ("existential_possessives", _transform_existential_possessives, _applicability_existential_possessives),
        ("possessives_for_post", _transform_possessives_for_post, _applicability_possessives_for_post),
        ("possessives_for_pre", _transform_possessives_for_pre, _applicability_possessives_for_pre),
        ("possessives_belong", _transform_possessives_belong, _applicability_possessives_belong),
        ("mass_noun_plurals", _transform_mass_noun_plurals, _applicability_mass_noun_plurals),
        ("that_resultative_past_participle", _transform_that_resultative_past_participle, _applicability_that_resultative_past_participle),
        ("medial_object_perfect", _transform_medial_object_perfect, _applicability_medial_object_perfect),
        ("serial_verb_give", _transform_serial_verb_give, _applicability_serial_verb_give),
        ("serial_verb_go", _transform_serial_verb_go, _applicability_serial_verb_go),
        ("transitive_suffix", _transform_transitive_suffix, _applicability_transitive_suffix),
        ("shadow_pronouns", _transform_shadow_pronouns, _applicability_shadow_pronouns),
        ("one_relativizer", _transform_one_relativizer, _applicability_one_relativizer),
        ("analytic_whose_relativizer", _transform_analytic_whose_relativizer, _applicability_analytic_whose_relativizer),
        ("correlative_constructions", _transform_correlative_constructions, _applicability_correlative_constructions),
        ("doubly_filled_comp", _transform_doubly_filled_comp, _applicability_doubly_filled_comp),
        ("inverted_indirect_question", _transform_inverted_indirect_question, _applicability_inverted_indirect_question),
        ("clefting", _transform_clefting, _applicability_clefting),
        ("fronting_pobj", _transform_fronting_pobj, _applicability_fronting_pobj),
        ("superlative_before_matrix_head", _transform_superlative_before_matrix_head, _applicability_superlative_before_matrix_head),
        ("chaining_main_verbs", _transform_chaining_main_verbs, _applicability_chaining_main_verbs),
    ]
    for feature_id, trans, check in pairs:
        try:
            _register_transform(feature_id, trans, check)
        except KeyError:
            pass
    # No-op for every remaining feature (so all 200+ have a transform and applicability)
    from engine.grammar.registry import GRAMMAR_REGISTRY
    for fid in list(GRAMMAR_REGISTRY.keys()):
        if GRAMMAR_REGISTRY[fid].transform is None:
            try:
                _register_transform(fid, _transform_noop, _applicability_noop)
            except KeyError:
                pass


# Run at import so GRAMMAR_REGISTRY gets transform/applicability_check for these features
_register_all_transforms()


def initialize_all_transforms() -> None:
    """Call this on app startup to ensure all transforms are registered."""
    # Simply importing this module triggers all register() calls
    pass


def apply_grammar(text: str, feature_id: str) -> str:
    """Apply a grammar feature transform to text. Returns original text if feature unknown or has no transform."""
    from engine.grammar.registry import GRAMMAR_REGISTRY

    if feature_id not in GRAMMAR_REGISTRY:
        return text
    feat = GRAMMAR_REGISTRY[feature_id]
    if feat.transform is None:
        return text
    return feat.transform(text)


# Auto-register all transforms on import
# (All register() calls above execute at module load time)