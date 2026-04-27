"""Tests for LLM output parsers."""

import pytest

from llm.parsers import (
    LikertParser,
    RecommendationListParser,
    FreeTextParser,
    get_parser,
)


class TestLikertParser:
    def test_just_number(self):
        parser = LikertParser()
        out = parser.parse("3")
        assert out["parsed_index"] == 3
        assert out["parsed_label"] == "neutral"
        assert out["is_valid"] is True
        assert out["parse_method"] == "number"

    def test_number_with_text(self):
        parser = LikertParser()
        out = parser.parse("4 - somewhat acceptable")
        assert out["parsed_index"] == 4
        assert out["parsed_label"] == "somewhat acceptable"
        assert out["is_valid"] is True
        assert out["parse_method"] == "number"

    def test_written_out_strongly_unacceptable(self):
        parser = LikertParser()
        out = parser.parse("strongly unacceptable")
        assert out["parsed_index"] == 1
        assert out["parsed_label"] == "strongly unacceptable"
        assert out["is_valid"] is True
        assert out["parse_method"] == "label"

    def test_i_think_2(self):
        parser = LikertParser()
        out = parser.parse("I think 2")
        assert out["parsed_index"] == 2
        assert out["parsed_label"] == "somewhat unacceptable"
        assert out["is_valid"] is True
        assert out["parse_method"] == "number"

    def test_not_a_valid_response(self):
        parser = LikertParser()
        out = parser.parse("not a valid response")
        assert out["parsed_label"] is None
        assert out["parsed_index"] is None
        assert out["is_valid"] is False
        assert out["parse_method"] == "failed"

    def test_empty(self):
        parser = LikertParser()
        out = parser.parse("")
        assert out["parsed_label"] is None
        assert out["parsed_index"] is None
        assert out["is_valid"] is False
        assert out["parse_method"] == "failed"


class TestRecommendationListParser:
    def test_numbered_list(self):
        parser = RecommendationListParser()
        raw = """1. The Shawshank Redemption
2. The Godfather
3. The Dark Knight"""
        out = parser.parse(raw)
        assert out["titles"] == [
            "The Shawshank Redemption",
            "The Godfather",
            "The Dark Knight",
        ]
        assert out["count"] == 3
        assert out["is_valid"] is True
        assert out["expected_count"] == 10

    def test_unnumbered_list(self):
        parser = RecommendationListParser()
        raw = """Inception
Interstellar
Parasite"""
        out = parser.parse(raw)
        assert out["titles"] == ["Inception", "Interstellar", "Parasite"]
        assert out["count"] == 3
        assert out["is_valid"] is True

    def test_empty(self):
        parser = RecommendationListParser()
        out = parser.parse("")
        assert out["titles"] == []
        assert out["count"] == 0
        assert out["is_valid"] is False

    def test_single_item(self):
        parser = RecommendationListParser()
        out = parser.parse("Only One Movie")
        assert out["titles"] == ["Only One Movie"]
        assert out["count"] == 1
        assert out["is_valid"] is True


class TestFreeTextParser:
    def test_normal_text(self):
        parser = FreeTextParser()
        raw = "This is a normal open-ended response with several words."
        out = parser.parse(raw)
        assert out["text"] == raw
        assert out["word_count"] == 9
        assert out["is_valid"] is True
        assert out["is_refusal"] is False

    def test_empty(self):
        parser = FreeTextParser()
        out = parser.parse("")
        assert out["text"] == ""
        assert out["word_count"] == 0
        assert out["is_valid"] is False
        assert out["is_refusal"] is False

    def test_refusal_i_cannot(self):
        parser = FreeTextParser()
        out = parser.parse("I cannot provide that information.")
        assert out["is_valid"] is True
        assert out["is_refusal"] is True

    def test_refusal_i_apologize(self):
        parser = FreeTextParser()
        out = parser.parse("I'm sorry, I can't help with that.")
        assert out["is_refusal"] is True

    def test_refusal_as_an_ai(self):
        parser = FreeTextParser()
        out = parser.parse("As an AI I don't have opinions.")
        assert out["is_refusal"] is True

    def test_refusal_not_appropriate(self):
        parser = FreeTextParser()
        out = parser.parse("That request is not appropriate.")
        assert out["is_refusal"] is True

    def test_refusal_i_must_decline(self):
        parser = FreeTextParser()
        out = parser.parse("I must decline to answer.")
        assert out["is_refusal"] is True


class TestGetParser:
    def test_returns_likert_parser(self):
        assert isinstance(get_parser("likert"), LikertParser)

    def test_returns_recommendation_list_parser(self):
        assert isinstance(get_parser("recommendation_list"), RecommendationListParser)

    def test_returns_free_text_parser(self):
        assert isinstance(get_parser("free_text"), FreeTextParser)

    def test_unknown_modality_defaults_to_free_text(self):
        assert isinstance(get_parser("unknown"), FreeTextParser)
