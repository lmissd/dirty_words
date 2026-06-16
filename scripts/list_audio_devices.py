"""List PortAudio devices visible to Python sounddevice."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import sounddevice as sd

from modules.utils.audio_devices import resolve_input_device
from modules.utils.config_loader import load_config
from modules.utils.errors import RobotError


def main() -> None:
    """Print audio devices and the auto-selected microphone when possible."""
    parser = argparse.ArgumentParser(description="List audio devices visible to sounddevice.")
    parser.add_argument("--config", default="config/config.yaml", help="Config file used to resolve auto input.")
    args = parser.parse_args()

    print(sd.query_devices())

    config_path = Path(args.config)
    if not config_path.exists():
        return

    try:
        config = load_config(config_path)
        channels = int(config.get("recording.channels", 1))
        device = resolve_input_device(config, "recording.device", channels=channels, sd_module=sd)
        wake_channels = int(config.get("wakeword.channels", channels))
        wake_device = resolve_input_device(
            config,
            "wakeword.device",
            fallback_key="recording.device",
            channels=wake_channels,
            sd_module=sd,
        )
    except RobotError as exc:
        print(f"\n自动选择麦克风失败：{exc}")
        return

    print(f"\n自动选择麦克风 device={device}")
    print(f"自动选择唤醒麦克风 device={wake_device}")
    _print_wakeword_input_check(config, wake_device, wake_channels)


def _print_wakeword_input_check(config, device: int | str | None, channels: int) -> None:
    sample_rate = int(config.get("wakeword.input_sample_rate", config.get("wakeword.sample_rate", 16000)))
    frame_ms = int(config.get("wakeword.frame_ms", 80))
    block_size = int(sample_rate * frame_ms / 1000)

    try:
        sd.check_input_settings(
            device=device,
            channels=channels,
            samplerate=sample_rate,
            dtype="int16",
        )
    except Exception as exc:
        print(f"openWakeWord 输入检查失败：{sample_rate}Hz/{channels}ch，{exc}")
        return

    print(f"openWakeWord 输入检查通过：{sample_rate}Hz/{channels}ch，{frame_ms}ms={block_size} samples")


if __name__ == "__main__":
    main()
