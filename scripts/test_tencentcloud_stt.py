"""Minimal Tencent Cloud STT test for Raspberry Pi."""

from __future__ import annotations

import argparse
import copy
import time
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.app import _build_speech_to_text
from modules.recorder.sounddevice_recorder import SoundDeviceRecorder
from modules.utils.config_loader import AppConfig, load_config
from modules.utils.errors import RobotError


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="最小化测试腾讯云语音识别。")
    parser.add_argument("--config", default="config/config.yaml", help="配置文件路径。")
    parser.add_argument("--countdown", type=int, default=5, help="开始录音前倒计时秒数。")
    parser.add_argument("--duration", type=float, default=4.0, help="固定录音时长，默认 4 秒。")
    parser.add_argument("--keep-audio", action="store_true", help="保留本次测试录音，默认测试后自动删除。")
    parser.add_argument("--text", default="饭团饭团", help="提示你对着麦克风说的话，仅用于屏幕提示。")
    return parser.parse_args()


def build_test_config(config: AppConfig, duration: float) -> AppConfig:
    """Build a temporary config for fixed-duration STT testing."""
    data = copy.deepcopy(config.data)
    recording = data.setdefault("recording", {})
    recording["engine"] = "sounddevice"
    recording["stop_on_silence"] = False
    recording["max_duration_seconds"] = duration
    recording["sample_rate"] = int(recording.get("sample_rate", 48000))
    recording["channels"] = int(recording.get("channels", 1))
    recording["device"] = recording.get("device", "auto")
    return AppConfig(data=data, path=config.path)


def main() -> int:
    """Record one short clip and send it to Tencent Cloud STT."""
    args = parse_args()
    config = load_config(Path(args.config))
    test_config = build_test_config(config, args.duration)
    recorder = SoundDeviceRecorder(test_config)
    stt = _build_speech_to_text(test_config)

    print(f"即将开始腾讯云 STT 测试，请准备说：{args.text}")
    print(f"倒计时：{args.countdown} 秒，录音时长：{args.duration:.1f} 秒")
    for remain in range(args.countdown, 0, -1):
        print(f"{remain}...")
        time.sleep(1)

    audio = recorder.record()
    print(f"已录音：{audio.path}")
    try:
        text = stt.transcribe(audio.path)
        print("腾讯云识别结果：")
        print(text)
        return 0
    except RobotError as exc:
        print(f"腾讯云 STT 测试失败：{exc}")
        return 2
    finally:
        if not args.keep_audio and audio.path.exists():
            audio.path.unlink()
            print("已删除测试录音。")
        elif args.keep_audio:
            print(f"已保留测试录音：{audio.path}")


if __name__ == "__main__":
    raise SystemExit(main())
