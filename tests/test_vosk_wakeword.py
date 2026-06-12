"""Tests for Vosk wake word helper functions."""

from __future__ import annotations

import unittest

from modules.wakeword.vosk_wakeword import _extract_vosk_text


class VoskWakeWordTests(unittest.TestCase):
    def test_extract_vosk_text(self) -> None:
        self.assertEqual(_extract_vosk_text('{"text": "范小团"}', "text"), "范小团")

    def test_extract_vosk_text_handles_invalid_json(self) -> None:
        self.assertEqual(_extract_vosk_text("not-json", "text"), "")


if __name__ == "__main__":
    unittest.main()
