"""Tests for wake word transcript matching."""

from __future__ import annotations

import unittest

from modules.wakeword.matcher import WakeMatcherConfig, match_wake_phrase, normalize_text


class WakeWordMatcherTests(unittest.TestCase):
    def test_normalize_text_removes_punctuation_and_spaces(self) -> None:
        self.assertEqual(normalize_text("饭 团，饭团！"), "饭团饭团")

    def test_match_exact_wake_phrase(self) -> None:
        config = WakeMatcherConfig(
            display_wake_word="饭团饭团",
            wake_phrases=["饭团饭团"],
            strict_match=False,
            wake_aliases=["饭团你好"],
            fuzzy_enabled=True,
            fuzzy_threshold=0.62,
            require_greeting=False,
            greeting_words=["你好", "你号"],
            subject_keywords=["饭团"],
        )

        self.assertEqual(match_wake_phrase("你好，饭团饭团。", config), "饭团饭团")

    def test_match_alias_when_not_strict(self) -> None:
        config = WakeMatcherConfig(
            display_wake_word="饭团饭团",
            wake_phrases=["饭团饭团"],
            strict_match=False,
            wake_aliases=["饭团你好"],
            fuzzy_enabled=True,
            fuzzy_threshold=0.62,
            require_greeting=False,
            greeting_words=["你好", "你号"],
            subject_keywords=["饭团"],
        )

        self.assertEqual(match_wake_phrase("饭团你好", config), "饭团饭团")

    def test_strict_match_rejects_alias_and_single_subject(self) -> None:
        config = WakeMatcherConfig(
            display_wake_word="饭团饭团",
            wake_phrases=["饭团饭团"],
            strict_match=True,
            wake_aliases=["饭团", "饭团你好"],
            fuzzy_enabled=True,
            fuzzy_threshold=0.62,
            require_greeting=False,
            greeting_words=["你好", "你号"],
            subject_keywords=["饭团"],
        )

        self.assertIsNone(match_wake_phrase("饭团你好呀", config))
        self.assertIsNone(match_wake_phrase("饭团", config))
        self.assertEqual(match_wake_phrase("饭团饭团", config), "饭团饭团")

    def test_empty_normalized_phrase_never_matches_any_text(self) -> None:
        config = WakeMatcherConfig(
            display_wake_word="饭团饭团",
            wake_phrases=["????"],
            strict_match=True,
            wake_aliases=[],
            fuzzy_enabled=False,
            fuzzy_threshold=0.62,
            require_greeting=False,
            greeting_words=["你好", "你号"],
            subject_keywords=[],
        )

        self.assertIsNone(match_wake_phrase("饭团你好呀", config))


if __name__ == "__main__":
    unittest.main()
