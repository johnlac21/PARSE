"""
Typo transform functions.

Each function takes text and optional word_p, char_p, and seed for deterministic
probabilistic typo application.
"""

import re
import random

# QWERTY keyboard adjacency map (lowercase letters only; apply to lowercase and preserve case)
QWERTY_ADJACENCY: dict[str, list[str]] = {
    "a": ["s", "q", "w", "z"],
    "b": ["v", "g", "h", "n"],
    "c": ["x", "d", "f", "v"],
    "d": ["s", "e", "r", "f", "c", "x"],
    "e": ["w", "r", "s", "d"],
    "f": ["d", "r", "t", "g", "v", "c"],
    "g": ["f", "t", "y", "h", "b", "v"],
    "h": ["g", "y", "u", "j", "n", "b"],
    "i": ["u", "o", "j", "k"],
    "j": ["h", "u", "i", "k", "m", "n"],
    "k": ["j", "i", "o", "l", "m"],
    "l": ["k", "o", "p"],
    "m": ["n", "j", "k"],
    "n": ["b", "h", "j", "m"],
    "o": ["i", "p", "k", "l"],
    "p": ["o", "l"],
    "q": ["w", "a"],
    "r": ["e", "t", "d", "f"],
    "s": ["a", "w", "e", "d", "z", "x"],
    "t": ["r", "y", "f", "g"],
    "u": ["y", "i", "h", "j"],
    "v": ["c", "f", "g", "b"],
    "w": ["q", "e", "a", "s"],
    "x": ["z", "s", "d", "c"],
    "y": ["t", "u", "g", "h"],
    "z": ["a", "s", "x"],
}


def _simple_tokenize(text: str) -> tuple[list[str], list[str]]:
    """Split into words (non-whitespace runs) and spaces after each word. Returns (words, spaces_after_each_word)."""
    words = re.findall(r"\S+", text)
    if not words:
        return [], []
    spaces: list[str] = []
    pos = 0
    for i, w in enumerate(words):
        idx = text.find(w, pos)
        pos = idx + len(w)
        if i + 1 < len(words):
            next_idx = text.find(words[i + 1], pos)
            spaces.append(text[pos:next_idx])
        else:
            spaces.append(text[pos:])
    return words, spaces


def typo_keyboard_prox(
    text: str, word_p: float = 0.15, char_p: float = 0.6, seed: int = 42
) -> str:
    """Replace some characters with adjacent keyboard keys (QWERTY)."""
    if not text.strip():
        return text
    rng = random.Random(seed)
    words, spaces = _simple_tokenize(text)
    out_words: list[str] = []
    for w in words:
        if rng.random() > word_p:
            out_words.append(w)
            continue
        chars = list(w)
        for i in range(len(chars)):
            if rng.random() > char_p:
                continue
            low = chars[i].lower()
            if low in QWERTY_ADJACENCY and QWERTY_ADJACENCY[low]:
                repl = rng.choice(QWERTY_ADJACENCY[low])
                chars[i] = repl.upper() if chars[i].isupper() else repl
        out_words.append("".join(chars))
    return _assemble(words, spaces, out_words)


def _assemble(
    orig_words: list[str], spaces: list[str], out_words: list[str]
) -> str:
    """Assemble output from words and spaces (spaces[i] after out_words[i])."""
    buf: list[str] = []
    for i, w in enumerate(out_words):
        buf.append(w)
        if i < len(spaces):
            buf.append(spaces[i])
    return "".join(buf)


def typo_char_swap(
    text: str, word_p: float = 0.15, char_p: float = 0.6, seed: int = 42
) -> str:
    """Swap two adjacent characters once per word (at a random position)."""
    if not text.strip():
        return text
    rng = random.Random(seed)
    words, spaces = _simple_tokenize(text)
    out_words: list[str] = []
    for w in words:
        if len(w) < 2 or rng.random() > word_p:
            out_words.append(w)
            continue
        idx = rng.randint(0, len(w) - 2)
        chars = list(w)
        chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
        out_words.append("".join(chars))
    return _assemble(words, spaces, out_words)


def typo_char_double(
    text: str, word_p: float = 0.15, char_p: float = 0.6, seed: int = 42
) -> str:
    """Double a random character in the word."""
    if not text.strip():
        return text
    rng = random.Random(seed)
    words, spaces = _simple_tokenize(text)
    out_words: list[str] = []
    for w in words:
        if len(w) < 1 or rng.random() > word_p:
            out_words.append(w)
            continue
        idx = rng.randint(0, len(w) - 1)
        out_words.append(w[: idx + 1] + w[idx] + w[idx + 1 :])
    return _assemble(words, spaces, out_words)


def typo_char_delete(
    text: str, word_p: float = 0.15, char_p: float = 0.6, seed: int = 42
) -> str:
    """Delete a random character (not first or last). Word length must be >= 3."""
    if not text.strip():
        return text
    rng = random.Random(seed)
    words, spaces = _simple_tokenize(text)
    out_words: list[str] = []
    for w in words:
        if len(w) < 3 or rng.random() > word_p:
            out_words.append(w)
            continue
        idx = rng.randint(1, len(w) - 2)
        out_words.append(w[:idx] + w[idx + 1 :])
    return _assemble(words, spaces, out_words)


def typo_whitespace(
    text: str, word_p: float = 0.15, char_p: float = 0.6, seed: int = 42
) -> str:
    """Randomly remove spaces between words or add extra spaces (word_p per space)."""
    if not text.strip():
        return text
    rng = random.Random(seed)
    words, spaces = _simple_tokenize(text)
    new_spaces: list[str] = []
    for i in range(len(spaces)):
        s = spaces[i]
        # Only modify between-word spaces (not trailing, index < len(words)-1)
        if i < len(words) - 1 and s and word_p > 0:
            if rng.random() < word_p:
                new_spaces.append("")
            elif rng.random() < char_p:
                new_spaces.append(s + " ")
            else:
                new_spaces.append(s)
        else:
            new_spaces.append(s)
    return _assemble(words, new_spaces, words)


def typo_typoglycemia(
    text: str, word_p: float = 0.15, char_p: float = 0.6, seed: int = 42
) -> str:
    """Keep first and last letter, shuffle middle letters (words length >= 4)."""
    if not text.strip():
        return text
    rng = random.Random(seed)
    words, spaces = _simple_tokenize(text)
    out_words: list[str] = []
    for w in words:
        if len(w) < 4 or rng.random() > word_p:
            out_words.append(w)
            continue
        mid = list(w[1:-1])
        rng.shuffle(mid)
        out_words.append(w[0] + "".join(mid) + w[-1])
    return _assemble(words, spaces, out_words)


def apply_typo(text: str, feature_name: str, seed: int = 42) -> str:
    """Apply a typo feature to text by name (uses registry defaults)."""
    from engine.typos.registry import TYPO_REGISTRY

    if feature_name not in TYPO_REGISTRY:
        return text
    feat = TYPO_REGISTRY[feature_name]
    return feat.transform(
        text,
        word_p=feat.default_word_p,
        char_p=feat.default_char_p,
        seed=seed,
    )
