"""Tests for sounddevice recorder helpers."""

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from modules.recorder.base import PcmAudioBuffer
from modules.recorder.sounddevice_recorder import SoundDeviceRecorder
from modules.utils.config_loader import AppConfig


class SoundDeviceRecorderTests(unittest.TestCase):
    def test_prepend_pre_roll_adds_trigger_audio_to_recording(self) -> None:
        recorder = SoundDeviceRecorder(
            AppConfig(data={}, path=Path("config/config.example.yaml"))
        )
        main_audio = np.array([[3], [4]], dtype=np.int16)
        pre_roll = PcmAudioBuffer(
            data=np.array([1, 2], dtype=np.int16).tobytes(),
            sample_rate=16000,
            channels=1,
        )

        combined = recorder._prepend_pre_roll(main_audio, pre_roll, 16000, 1)

        self.assertEqual(combined.reshape(-1).tolist(), [1, 2, 3, 4])

    def test_prepend_pre_roll_skips_mismatched_audio(self) -> None:
        recorder = SoundDeviceRecorder(
            AppConfig(data={}, path=Path("config/config.example.yaml"))
        )
        main_audio = np.array([[3], [4]], dtype=np.int16)
        pre_roll = PcmAudioBuffer(
            data=np.array([1, 2], dtype=np.int16).tobytes(),
            sample_rate=48000,
            channels=1,
        )

        combined = recorder._prepend_pre_roll(main_audio, pre_roll, 16000, 1)

        self.assertIs(combined, main_audio)


if __name__ == "__main__":
    unittest.main()
