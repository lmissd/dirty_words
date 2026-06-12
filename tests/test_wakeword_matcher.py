"""Tests for wake word transcript matching."""

from __future__ import annotations

import unittest

from modules.wakeword.matcher import WakeMatcherConfig, match_wake_phrase, normalize_text


class WakeWordMatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = WakeMatcherConfig(
            display_wake_word="范小团你好",
            wake_phrases=["范小团你好"],
            wake_aliases=["饭小团你好", "但小团你好", "分小团你好", "小团你好"],
            fuzzy_enabled=True,
            fuzzy_threshold=0.62,
            require_greeting=True,
            greeting_words=["你好", "你号"],
            subject_keywords=["小团"],
        )

    def test_normalize_text_removes_punctuation_and_spaces(self) -> None:
        self.assertEqual(normalize_text("范 小 团，你好！"), "范小团你好")

    def test_match_exact_wake_phrase(self) -> None:
        self.assertEqual(match_wake_phrase("你好，范小团你好。", self.config), "范小团你好")

    def test_match_alias_wake_phrase(self) -> None:
        self.assertEqual(match_wake_phrase("但小团你好", self.config), "范小团你好")

    def test_match_subject_plus_greeting(self) -> None:
        self.assertEqual(match_wake_phrase("办 小团 你号", self.config), "范小团你好")

    def test_greeting_only_does_not_match(self) -> None:
        self.assertIsNone(match_wake_phrase("老师你好", self.config))

    def test_no_match_returns_none(self) -> None:
        self.assertIsNone(match_wake_phrase("你好，小朋友。", self.config))


if __name__ == "__main__":
    unittest.main()
