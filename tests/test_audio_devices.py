"""Tests for audio device selection helpers."""

from __future__ import annotations

import unittest
from pathlib import Path

from modules.utils.audio_devices import resolve_input_device
from modules.utils.config_loader import AppConfig
from modules.utils.errors import AudioInputError


class FakeDefault:
    def __init__(self, input_index: int) -> None:
        self.device = [input_index, -1]


class FakeSoundDevice:
    def __init__(self, devices: list[dict], default_input: int = -1) -> None:
        self.devices = devices
        self.default = FakeDefault(default_input)

    def query_devices(self, device=None, kind=None):
        if device is None:
            return self.devices
        if isinstance(device, str) and device.lstrip("-").isdigit():
            device = int(device)
        if isinstance(device, int):
            return self.devices[device]
        for item in self.devices:
            if item["name"] == device:
                return item
        raise ValueError(f"Unknown device: {device}")


class AudioDeviceSelectionTests(unittest.TestCase):
    def test_auto_prefers_usb_input_device(self) -> None:
        config = AppConfig(data={"recording": {"device": "auto"}}, path=Path("config/config.example.yaml"))
        sd = FakeSoundDevice(
            [
                {"name": "bcm2835 Headphones", "max_input_channels": 0, "max_output_channels": 8},
                {"name": "Built-in Mic", "max_input_channels": 1, "max_output_channels": 0},
                {"name": "USB Composite Device", "max_input_channels": 1, "max_output_channels": 2},
            ],
            default_input=1,
        )

        device = resolve_input_device(config, "recording.device", channels=1, sd_module=sd)

        self.assertEqual(device, 2)

    def test_auto_falls_back_to_default_input(self) -> None:
        config = AppConfig(data={"recording": {"device": "auto"}}, path=Path("config/config.example.yaml"))
        sd = FakeSoundDevice(
            [
                {"name": "Input A", "max_input_channels": 1, "max_output_channels": 0},
                {"name": "Input B", "max_input_channels": 1, "max_output_channels": 0},
            ],
            default_input=1,
        )

        device = resolve_input_device(config, "recording.device", channels=1, sd_module=sd)

        self.assertEqual(device, 1)

    def test_explicit_device_is_validated(self) -> None:
        config = AppConfig(data={"recording": {"device": 0}}, path=Path("config/config.example.yaml"))
        sd = FakeSoundDevice(
            [{"name": "Output Only", "max_input_channels": 0, "max_output_channels": 2}],
        )

        with self.assertRaises(AudioInputError):
            resolve_input_device(config, "recording.device", channels=1, sd_module=sd)

    def test_fallback_key_is_used(self) -> None:
        config = AppConfig(data={"recording": {"device": "auto"}}, path=Path("config/config.example.yaml"))
        sd = FakeSoundDevice(
            [{"name": "USB Microphone", "max_input_channels": 1, "max_output_channels": 0}],
        )

        device = resolve_input_device(
            config,
            "wakeword.device",
            fallback_key="recording.device",
            channels=1,
            sd_module=sd,
        )

        self.assertEqual(device, 0)

    def test_auto_error_explains_output_only_device_list(self) -> None:
        config = AppConfig(data={"recording": {"device": "auto"}}, path=Path("config/config.example.yaml"))
        sd = FakeSoundDevice(
            [{"name": "bcm2835 Headphones", "max_input_channels": 0, "max_output_channels": 8}],
        )

        with self.assertRaises(AudioInputError) as context:
            resolve_input_device(config, "recording.device", channels=1, sd_module=sd)

        message = str(context.exception)
        self.assertIn("当前只识别到输出设备", message)
        self.assertIn("arecord -l", message)


if __name__ == "__main__":
    unittest.main()
