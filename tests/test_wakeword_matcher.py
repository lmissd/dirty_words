"""Tests for wake word transcript matching."""

from __future__ import annotations

import unittest

from modules.wakeword.stt_wakeword import match_wake_word, normalize_text


class WakeWordMatcherTests(unittest.TestCase):
    def test_normalize_text_removes_punctuation_and_spaces(self) -> None:
        self.assertEqual(normalize_text("范 小 团！"), "范小团")

    def test_match_chinese_wake_word(self) -> None:
        self.assertEqual(match_wake_word("你好，范小团。", ["范小团"]), "范小团")

    def test_no_match_returns_none(self) -> None:
        self.assertIsNone(match_wake_word("你好，小朋友。", ["范小团"]))


if __name__ == "__main__":
    unittest.main()
