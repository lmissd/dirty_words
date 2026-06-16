"""Collect local wake word recordings for custom model training."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.utils.audio_devices import resolve_input_device
from modules.utils.config_loader import load_config
from modules.utils.disk import ensure_free_space

DEFAULT_OUTPUT_DIR = Path("training_data/wakeword/fantuan_fantuan")
DEFAULT_WAKE_PHRASE = "饭团饭团"


@dataclass(frozen=True, slots=True)
class RecordingPlan:
    """Resolved settings for wake word sample collection."""

    phrase: str
    output_dir: Path
    duration_seconds: float
    sample_rate: int
    channels: int
    count: int
    start_index: int
    device: int | str | None


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="连续采集 openWakeWord 自定义唤醒词训练样本。")
    parser.add_argument("--config", default="config/config.yaml", help="配置文件路径。")
    parser.add_argument("--phrase", default=None, help=f"要录制的唤醒词，默认 {DEFAULT_WAKE_PHRASE}。")
    parser.add_argument("--count", type=int, default=30, help="计划采集条数，默认 30 条。")
    parser.add_argument("--duration", type=float, default=2.0, help="每条录音时长，默认 2 秒。")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="输出目录。")
    parser.add_argument("--start-index", type=int, default=None, help="起始编号，默认自动续接。")
    parser.add_argument("--playback", action="store_true", help="每条录完后播放试听。")
    parser.add_argument("--no-confirm", action="store_true", help="录完后不询问保留/重录，直接保存。")
    return parser.parse_args()


def main() -> None:
    """Collect wake phrase samples interactively."""
    args = parse_args()
    config = load_config(Path(args.config))

    import sounddevice as sd
    import soundfile as sf

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_free_space(output_dir)

    phrase = str(args.phrase or config.get("wakeword.display_wake_word", DEFAULT_WAKE_PHRASE))
    sample_rate = int(config.get("wakeword.input_sample_rate", config.get("wakeword.sample_rate", 48000)))
    channels = int(config.get("wakeword.channels", config.get("recording.channels", 1)))
    device = resolve_input_device(
        config,
        "wakeword.device",
        fallback_key="recording.device",
        channels=channels,
        sd_module=sd,
    )
    start_index = args.start_index if args.start_index is not None else next_sample_index(output_dir)
    plan = RecordingPlan(
        phrase=phrase,
        output_dir=output_dir,
        duration_seconds=args.duration,
        sample_rate=sample_rate,
        channels=channels,
        count=args.count,
        start_index=start_index,
        device=device,
    )

    print_intro(plan)
    metadata_path = output_dir / "metadata.csv"
    accepted = 0
    current_index = start_index

    while accepted < plan.count:
        print(f"\n第 {accepted + 1}/{plan.count} 条，文件编号 {current_index:04d}")
        command = input(f"按回车开始录音；输入 q 退出；输入 s 跳过这个编号。\n请准备说：{plan.phrase}\n> ").strip().lower()
        if command == "q":
            break
        if command == "s":
            current_index += 1
            continue

        output_path = output_dir / f"fantuan_fantuan_{current_index:04d}.wav"
        record_one_sample(plan, output_path, sd=sd, sf=sf)

        if args.playback:
            play_sample(config, output_path)

        if args.no_confirm:
            action = "keep"
        else:
            action = confirm_sample_action(output_path)

        if action == "keep":
            append_metadata(metadata_path, output_path, plan)
            accepted += 1
            current_index += 1
            print(f"已保存：{output_path}")
        elif action == "skip":
            current_index += 1
            print("已删除本条录音，并跳过这个编号。")
        else:
            output_path.unlink(missing_ok=True)
            print("已删除本条录音，准备重录同一编号。")

    print(f"\n采集结束：本次保留 {accepted} 条样本，目录：{output_dir}")
    print(f"元数据文件：{metadata_path}")


def print_intro(plan: RecordingPlan) -> None:
    """Print human-friendly recording instructions."""
    print("=== 饭团饭团唤醒词样本采集 ===")
    print(f"唤醒词：{plan.phrase}")
    print(f"输出目录：{plan.output_dir}")
    print(f"计划采集：{plan.count} 条")
    print(f"每条时长：{plan.duration_seconds:.1f} 秒")
    print(f"麦克风 device={plan.device}，采样率={plan.sample_rate}，声道数={plan.channels}")
    print("建议录制时变化距离、音量和语速，例如近一点、远一点、正常说、小声说。")
    print("训练素材属于个人音频，不要提交到 GitHub。")


def record_one_sample(plan: RecordingPlan, output_path: Path, *, sd, sf) -> None:
    """Record one wake phrase sample to a WAV file."""
    frames = int(plan.sample_rate * plan.duration_seconds)
    for second in range(3, 0, -1):
        print(f"{second}...")
        time.sleep(1)

    print(f"开始录音，请说：{plan.phrase}")
    audio = sd.rec(
        frames,
        samplerate=plan.sample_rate,
        channels=plan.channels,
        device=plan.device,
        dtype="float32",
    )
    sd.wait()
    sf.write(output_path, audio, plan.sample_rate)
    print(f"录制完成：{output_path}")


def confirm_sample_action(output_path: Path) -> str:
    """Ask whether to keep, retry, or skip the current sample."""
    while True:
        answer = input("保留这条录音吗？直接回车=保留，r=重录，d=删除并跳过编号，q=退出脚本。\n> ").strip().lower()
        if answer in {"", "y", "yes"}:
            return "keep"
        if answer == "r":
            return "retry"
        if answer == "d":
            output_path.unlink(missing_ok=True)
            return "skip"
        if answer == "q":
            raise SystemExit("用户退出采集。")
        print("请输入回车、r、d 或 q。")


def play_sample(config, output_path: Path) -> None:
    """Play back a recorded sample when playback is requested."""
    from modules.utils.audio_player import AudioPlayer
    from modules.utils.errors import AudioOutputError

    try:
        AudioPlayer(config).play(output_path)
    except AudioOutputError as exc:
        print(f"试听播放失败，但录音已保存：{exc}")


def append_metadata(metadata_path: Path, output_path: Path, plan: RecordingPlan) -> None:
    """Append one accepted recording to metadata.csv."""
    exists = metadata_path.exists()
    with metadata_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "file",
                "phrase",
                "sample_rate",
                "channels",
                "duration_seconds",
                "created_at",
            ],
        )
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "file": output_path.name,
                "phrase": plan.phrase,
                "sample_rate": plan.sample_rate,
                "channels": plan.channels,
                "duration_seconds": f"{plan.duration_seconds:.3f}",
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )


def next_sample_index(output_dir: Path) -> int:
    """Return the next available numeric sample index in the output directory."""
    indexes: list[int] = []
    for path in output_dir.glob("fantuan_fantuan_*.wav"):
        try:
            indexes.append(int(path.stem.rsplit("_", 1)[-1]))
        except ValueError:
            continue
    return max(indexes, default=0) + 1


if __name__ == "__main__":
    main()
