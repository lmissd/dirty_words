"""Record the preset greeting voice used by wake-greeting mode."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.utils.audio_devices import resolve_input_device
from modules.utils.config_loader import load_config
from modules.utils.disk import ensure_free_space


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="录制唤醒后的固定问候语音。")
    parser.add_argument("--config", default="config/config.yaml", help="配置文件路径。")
    parser.add_argument("--duration", type=float, default=3.0, help="录音时长，默认 3 秒。")
    parser.add_argument("--output", default=None, help="输出 wav 路径，默认读取 greeting.audio_path。")
    parser.add_argument("--no-prompt", action="store_true", help="不等待回车，直接倒计时录音。")
    parser.add_argument("--playback", action="store_true", help="录完后立即播放试听。")
    return parser.parse_args()


def main() -> None:
    """Record a greeting wav file from the configured microphone."""
    args = parse_args()
    config = load_config(Path(args.config))
    output_path = Path(args.output or str(config.get("greeting.audio_path", "assets/audio/greeting.wav")))
    sample_rate = int(config.get("recording.sample_rate", 48000))
    channels = int(config.get("recording.channels", 1))
    frames = int(sample_rate * args.duration)

    ensure_free_space(output_path.parent)

    import sounddevice as sd
    import soundfile as sf

    device = resolve_input_device(config, "recording.device", channels=channels, sd_module=sd)

    print(f"准备录制问候语：{config.get('greeting.text', '小朋友你好')}")
    print(f"输出文件：{output_path}")
    print(f"麦克风 device={device}，采样率={sample_rate}，声道数={channels}，时长={args.duration:.1f} 秒")
    if not args.no_prompt:
        input("按回车后开始录音，请说“小朋友你好”。")

    for second in range(3, 0, -1):
        print(f"{second}...")
        time.sleep(1)

    print("开始录音，请说：小朋友你好")
    audio = sd.rec(frames, samplerate=sample_rate, channels=channels, device=device, dtype="float32")
    sd.wait()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, audio, sample_rate)
    print(f"录制完成：{output_path}")

    if args.playback:
        from modules.utils.audio_player import AudioPlayer
        from modules.utils.errors import AudioOutputError

        try:
            AudioPlayer(config).play(output_path)
        except AudioOutputError as exc:
            print(f"试听播放失败，但录音已保存：{exc}")


if __name__ == "__main__":
    main()
