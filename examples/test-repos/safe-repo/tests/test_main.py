"""Tests for pytoolkit core functions."""

import pytest

from src.main import greet, word_count


class TestGreet:
    def test_basic_greeting(self):
        assert greet("World") == "Hello, World!"

    def test_greeting_with_name(self):
        assert greet("Alice") == "Hello, Alice!"

    def test_strips_whitespace(self):
        assert greet("  Bob  ") == "Hello, Bob!"

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="Name cannot be empty"):
            greet("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="Name cannot be empty"):
            greet("   ")


class TestWordCount:
    def test_simple_sentence(self):
        result = word_count("the cat sat on the mat")
        assert result["the"] == 2
        assert result["cat"] == 1

    def test_punctuation_stripped(self):
        result = word_count("hello, world! hello.")
        assert result["hello"] == 2
        assert result["world"] == 1

    def test_empty_string(self):
        assert word_count("") == {}

    def test_case_insensitive(self):
        result = word_count("Hello hello HELLO")
        assert result["hello"] == 3
