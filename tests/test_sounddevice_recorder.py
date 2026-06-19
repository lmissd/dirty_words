"""Tests for sounddevice recorder helpers."""

from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

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

    def test_record_until_silence_uses_pre_roll_and_stops_after_silence(self) -> None:
        block_frames = 3200
        pre_roll = PcmAudioBuffer(
            data=np.full(block_frames, 500, dtype=np.int16).tobytes(),
            sample_rate=16000,
            channels=1,
        )
        sd = FakeSoundDeviceModule(
            chunks=[
                np.full(block_frames, 500, dtype=np.int16).tobytes(),
                np.zeros(block_frames, dtype=np.int16).tobytes(),
                np.zeros(block_frames, dtype=np.int16).tobytes(),
            ]
        )
        recorder = SoundDeviceRecorder(
            AppConfig(
                data={
                    "recording": {
                        "sample_rate": 16000,
                        "channels": 1,
                        "device": "auto",
                        "stop_on_silence": True,
                        "max_duration_seconds": 5,
                        "min_duration_seconds": 0.5,
                        "silence_duration_seconds": 0.4,
                        "silence_rms_threshold": 100,
                        "block_seconds": 0.2,
                    }
                },
                path=Path("config/config.example.yaml"),
            ),
            sd_module=sd,
        )

        audio = recorder._record_until_silence(
            sd,
            sample_rate=16000,
            channels=1,
            device=0,
            max_duration=5,
            pre_roll_audio=pre_roll,
        )

        self.assertEqual(audio.shape, (block_frames * 4, 1))
        self.assertEqual(audio[:3].reshape(-1).tolist(), [500, 500, 500])


class FakeRawInputStream:
    def __init__(self, module, callback, blocksize) -> None:
        self.module = module
        self.callback = callback
        self.blocksize = blocksize

    def __enter__(self):
        for chunk in self.module.chunks:
            self.callback(chunk, self.blocksize, None, None)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class FakeSoundDeviceModule:
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.devices = [
            {"name": "USB Audio Device", "max_input_channels": 1, "max_output_channels": 0}
        ]
        self.default = SimpleNamespace(device=[0, 0])

    def query_devices(self, device=None, kind=None):
        if device is None:
            return self.devices
        return self.devices[int(device)]

    def RawInputStream(self, **kwargs):
        return FakeRawInputStream(self, kwargs["callback"], kwargs["blocksize"])


if __name__ == "__main__":
    unittest.main()
