"""Tests for local speech activity helpers."""

from __future__ import annotations

import unittest

from modules.recorder.speech_activity import _pcm16_rms


class SpeechActivityTests(unittest.TestCase):
    def test_pcm16_rms_silence(self) -> None:
        self.assertEqual(_pcm16_rms(b"\x00\x00" * 4), 0)

    def test_pcm16_rms_detects_energy(self) -> None:
        data = b"".join(int(1000).to_bytes(2, "little", signed=True) for _ in range(4))
        self.assertEqual(_pcm16_rms(data), 1000)


if __name__ == "__main__":
    unittest.main()
