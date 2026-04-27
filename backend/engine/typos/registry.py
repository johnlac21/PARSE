"""
TypoFeature dataclass and TYPO_REGISTRY.

Maps typo feature names to TypoFeature definitions.
"""

from dataclasses import dataclass
from typing import Callable

from engine.typos.transforms import (
    typo_char_delete,
    typo_char_double,
    typo_char_swap,
    typo_keyboard_prox,
    typo_typoglycemia,
    typo_whitespace,
)

TYPO_REGISTRY: dict[str, "TypoFeature"] = {}


@dataclass
class TypoFeature:
    """Describes a typo transform: id, name, description, example, and transform function."""

    id: str
    name: str
    description: str
    example: str
    transform: Callable[..., str]
    default_word_p: float
    default_char_p: float


def _register(feature: TypoFeature) -> None:
    TYPO_REGISTRY[feature.id] = feature


_register(
    TypoFeature(
        id="typo_keyboard_prox",
        name="Keyboard proximity",
        description="Replace characters with adjacent QWERTY keys.",
        example="recommend a film → recommend a fklm",
        transform=typo_keyboard_prox,
        default_word_p=0.15,
        default_char_p=0.6,
    )
)
_register(
    TypoFeature(
        id="typo_char_swap",
        name="Character swap",
        description="Swap two adjacent characters in a word.",
        example="recommend → reocmmend",
        transform=typo_char_swap,
        default_word_p=0.15,
        default_char_p=0.6,
    )
)
_register(
    TypoFeature(
        id="typo_char_double",
        name="Character double",
        description="Double a random character in a word.",
        example="movie → moovie",
        transform=typo_char_double,
        default_word_p=0.15,
        default_char_p=0.6,
    )
)
_register(
    TypoFeature(
        id="typo_char_delete",
        name="Character delete",
        description="Delete a random character (not first or last) in words of length >= 3.",
        example="recommend → recomend",
        transform=typo_char_delete,
        default_word_p=0.15,
        default_char_p=0.6,
    )
)
_register(
    TypoFeature(
        id="typo_whitespace",
        name="Whitespace",
        description="Remove spaces between words or add extra spaces.",
        example="I want a movie → I wanta movie or I  want a movie",
        transform=typo_whitespace,
        default_word_p=0.15,
        default_char_p=0.6,
    )
)
_register(
    TypoFeature(
        id="typo_typoglycemia",
        name="Typoglycemia",
        description="Keep first and last letter, shuffle middle letters (words length >= 4).",
        example="recommend → rceomemnd",
        transform=typo_typoglycemia,
        default_word_p=0.15,
        default_char_p=0.6,
    )
)
