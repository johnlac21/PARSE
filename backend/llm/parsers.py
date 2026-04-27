"""Output parsers for LLM responses (Likert, recommendation lists, free text)."""

from abc import ABC, abstractmethod
import re


class OutputParser(ABC):
    @abstractmethod
    def parse(self, raw_response: str) -> dict:
        """Returns structured output for storage and comparison."""
        ...


class LikertParser(OutputParser):
    """
    Parses Likert scale responses (1-5).
    Handles various formats:
    - Just the number: "3"
    - Number with text: "3 - Somewhat acceptable"
    - Written out: "strongly acceptable" (map to 5)
    - With explanation: "I would rate this a 4 because..."
    """

    LABEL_MAP = {
        "strongly unacceptable": 1,
        "completely unacceptable": 1,
        "very unacceptable": 1,
        "somewhat unacceptable": 2,
        "slightly unacceptable": 2,
        "mostly unacceptable": 2,
        "neutral": 3,
        "neither": 3,
        "uncertain": 3,
        "somewhat acceptable": 4,
        "slightly acceptable": 4,
        "mostly acceptable": 4,
        "strongly acceptable": 5,
        "completely acceptable": 5,
        "very acceptable": 5,
        "perfectly acceptable": 5,
    }

    def parse(self, raw: str) -> dict:
        """
        Strategy:
        1. Try to extract a number 1-5 from the response
        2. If no number, try to match label strings
        3. If neither works, mark as invalid

        Returns: {"parsed_label": str | None, "parsed_index": int | None, "is_valid": bool, "parse_method": str}
        """
        raw_clean = raw.strip().lower()

        # Method 1: Direct number extraction
        number_match = re.search(r"\b([1-5])\b", raw_clean)
        if number_match:
            idx = int(number_match.group(1))
            label = self._index_to_label(idx)
            return {
                "parsed_label": label,
                "parsed_index": idx,
                "is_valid": True,
                "parse_method": "number",
            }

        # Method 2: Label matching
        for label, idx in self.LABEL_MAP.items():
            if label in raw_clean:
                return {
                    "parsed_label": label,
                    "parsed_index": idx,
                    "is_valid": True,
                    "parse_method": "label",
                }

        # Method 3: Failed
        return {
            "parsed_label": None,
            "parsed_index": None,
            "is_valid": False,
            "parse_method": "failed",
        }

    def _index_to_label(self, idx: int) -> str:
        labels = {
            1: "strongly unacceptable",
            2: "somewhat unacceptable",
            3: "neutral",
            4: "somewhat acceptable",
            5: "strongly acceptable",
        }
        return labels.get(idx, "unknown")


# TODO(v2): Wire up to user-selectable modality. Currently
# scaffolded but unreachable — only "likert" is exposed in the API.
class RecommendationListParser(OutputParser):
    """
    Parses movie/item recommendation lists.
    Expected format: one item per line, possibly numbered.
    """

    def parse(self, raw: str) -> dict:
        lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]
        # Remove numbering: "1. Movie Title" → "Movie Title"
        titles = []
        for line in lines:
            cleaned = re.sub(r"^\d+[\.\)\-]\s*", "", line).strip()
            if cleaned:
                titles.append(cleaned)
        return {
            "titles": titles,
            "count": len(titles),
            "is_valid": len(titles) > 0,
            "expected_count": 10,  # default expectation
        }


# TODO(v2): Wire up to user-selectable modality. Currently
# scaffolded but unreachable — only "likert" is exposed in the API.
class FreeTextParser(OutputParser):
    """For open-ended responses — minimal parsing, stores raw text."""

    def parse(self, raw: str) -> dict:
        text = raw.strip()
        return {
            "text": text,
            "word_count": len(text.split()),
            "is_valid": bool(text),
            "is_refusal": self._detect_refusal(text),
        }

    def _detect_refusal(self, text: str) -> bool:
        refusal_patterns = [
            r"I cannot",
            r"I can't",
            r"I'm sorry",
            r"I apologize",
            r"As an AI",
            r"As a language model",
            r"not appropriate",
            r"I don't think I should",
            r"I'm not able to",
            r"I must decline",
            r"I won't be able",
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in refusal_patterns)


# NOTE: Only "likert" is currently exposed via the API. The other
# parsers remain registered for forward compatibility — see the
# README "Roadmap" section.
def get_parser(task_modality: str) -> OutputParser:
    """
    Return the OutputParser for the given task modality.

    Supported modalities: "likert", "recommendation_list", "free_text".
    Unknown modalities default to FreeTextParser.
    """
    parsers = {
        "likert": LikertParser(),
        "recommendation_list": RecommendationListParser(),
        "free_text": FreeTextParser(),
    }
    return parsers.get(task_modality, FreeTextParser())
