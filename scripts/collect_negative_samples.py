"""Collect negative wake word samples for custom model training."""

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

DEFAULT_OUTPUT_DIR = Path("training_data/wakeword/negative")
DEFAULT_WAKE_PHRASE = "饭团饭团"


@dataclass(frozen=True, slots=True)
class PromptSpec:
    """One negative-sample prompt."""

    category: str
    prompt_text: str
    spoken_text: str


@dataclass(frozen=True, slots=True)
class RecordingPlan:
    """Resolved settings for negative sample collection."""

    wake_phrase: str
    output_dir: Path
    duration_seconds: float
    sample_rate: int
    channels: int
    count: int
    device: int | str | None
    prompts: list[PromptSpec]


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="连续采集 openWakeWord 负样本训练素材。")
    parser.add_argument("--config", default="config/config.yaml", help="配置文件路径。")
    parser.add_argument("--count", type=int, default=30, help="计划采集条数，默认 30 条。")
    parser.add_argument("--duration", type=float, default=2.0, help="每条录音时长，默认 2 秒。")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="输出目录。")
    parser.add_argument(
        "--group",
        choices=("mixed", "near_miss", "other_speech", "ambient"),
        default="mixed",
        help="采集类型，默认 mixed。",
    )
    parser.add_argument("--playback", action="store_true", help="每条录完后播放试听。")
    parser.add_argument("--no-confirm", action="store_true", help="录完后不询问保留/重录，直接保存。")
    return parser.parse_args()


def main() -> None:
    """Collect negative wake phrase samples interactively."""
    args = parse_args()
    config = load_config(Path(args.config))

    import sounddevice as sd
    import soundfile as sf

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_free_space(output_dir)

    wake_phrase = str(config.get("wakeword.display_wake_word", DEFAULT_WAKE_PHRASE))
    sample_rate = int(config.get("wakeword.input_sample_rate", config.get("wakeword.sample_rate", 48000)))
    channels = int(config.get("wakeword.channels", config.get("recording.channels", 1)))
    device = resolve_input_device(
        config,
        "wakeword.device",
        fallback_key="recording.device",
        channels=channels,
        sd_module=sd,
    )
    prompts = build_prompt_plan(args.group, wake_phrase)
    plan = RecordingPlan(
        wake_phrase=wake_phrase,
        output_dir=output_dir,
        duration_seconds=args.duration,
        sample_rate=sample_rate,
        channels=channels,
        count=args.count,
        device=device,
        prompts=prompts,
    )

    print_intro(plan, args.group)
    metadata_path = output_dir / "metadata.csv"
    accepted = 0
    category_indexes = {spec.category: next_sample_index(output_dir / spec.category, spec.category) for spec in prompts}

    while accepted < plan.count:
        prompt = prompts[accepted % len(prompts)]
        current_index = category_indexes[prompt.category]
        category_dir = output_dir / prompt.category
        category_dir.mkdir(parents=True, exist_ok=True)
        output_path = category_dir / f"{prompt.category}_{current_index:04d}.wav"

        print(f"\n第 {accepted + 1}/{plan.count} 条，类型 {prompt.category}，文件编号 {current_index:04d}")
        command = input(f"按回车开始录音；输入 q 退出；输入 s 跳过这一条。\n{prompt.prompt_text}\n> ").strip().lower()
        if command == "q":
            break
        if command == "s":
            category_indexes[prompt.category] += 1
            continue

        record_one_sample(plan, prompt, output_path, sd=sd, sf=sf)

        if args.playback:
            play_sample(config, output_path)

        if args.no_confirm:
            action = "keep"
        else:
            action = confirm_sample_action(output_path)

        if action == "keep":
            append_metadata(metadata_path, output_path, plan, prompt)
            accepted += 1
            category_indexes[prompt.category] += 1
            print(f"已保存：{output_path}")
        elif action == "skip":
            category_indexes[prompt.category] += 1
            print("已删除本条录音，并跳过这个编号。")
        else:
            output_path.unlink(missing_ok=True)
            print("已删除本条录音，准备重录同一编号。")

    print(f"\n采集结束：本次保留 {accepted} 条负样本，目录：{output_dir}")
    print(f"元数据文件：{metadata_path}")


def print_intro(plan: RecordingPlan, group: str) -> None:
    """Print human-friendly recording instructions."""
    print("=== 饭团饭团负样本采集 ===")
    print(f"目标唤醒词：{plan.wake_phrase}")
    print(f"输出目录：{plan.output_dir}")
    print(f"采集模式：{group}")
    print(f"计划采集：{plan.count} 条")
    print(f"每条时长：{plan.duration_seconds:.1f} 秒")
    print(f"麦克风 device={plan.device}，采样率={plan.sample_rate}，声道数={plan.channels}")
    print("负样本不要说“饭团饭团”本身。推荐包含相似误触发词、普通说话和环境噪声。")
    print("训练素材属于个人音频，不要提交到 GitHub。")


def record_one_sample(plan: RecordingPlan, prompt: PromptSpec, output_path: Path, *, sd, sf) -> None:
    """Record one negative sample to a WAV file."""
    frames = int(plan.sample_rate * plan.duration_seconds)
    for second in range(3, 0, -1):
        print(f"{second}...")
        time.sleep(1)

    print(f"开始录音：{prompt.spoken_text}")
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


def append_metadata(metadata_path: Path, output_path: Path, plan: RecordingPlan, prompt: PromptSpec) -> None:
    """Append one accepted recording to metadata.csv."""
    exists = metadata_path.exists()
    with metadata_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "file",
                "category",
                "prompt_text",
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
                "file": output_path.relative_to(plan.output_dir).as_posix(),
                "category": prompt.category,
                "prompt_text": prompt.spoken_text,
                "sample_rate": plan.sample_rate,
                "channels": plan.channels,
                "duration_seconds": f"{plan.duration_seconds:.3f}",
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )


def next_sample_index(output_dir: Path, prefix: str) -> int:
    """Return the next available numeric sample index in one category directory."""
    indexes: list[int] = []
    for path in output_dir.glob(f"{prefix}_*.wav"):
        try:
            indexes.append(int(path.stem.rsplit("_", 1)[-1]))
        except ValueError:
            continue
    return max(indexes, default=0) + 1


def build_prompt_plan(group: str, wake_phrase: str) -> list[PromptSpec]:
    """Build a default negative prompt plan."""
    near_miss = [
        PromptSpec("near_miss", "请说相似词：饭团你好", "请说：饭团你好"),
        PromptSpec("near_miss", "请说相似词：饭桶饭桶", "请说：饭桶饭桶"),
        PromptSpec("near_miss", "请说相似词：范小团你好", "请说：范小团你好"),
        PromptSpec("near_miss", "请说相似词：反弹反弹", "请说：反弹反弹"),
        PromptSpec("near_miss", "请说相似词：小饭团", "请说：小饭团"),
    ]
    other_speech = [
        PromptSpec("other_speech", "请说普通句子：今天天气真不错", "请说：今天天气真不错"),
        PromptSpec("other_speech", "请说普通句子：我们一起去画画吧", "请说：我们一起去画画吧"),
        PromptSpec("other_speech", "请说普通句子：请把玩具收起来", "请说：请把玩具收起来"),
        PromptSpec("other_speech", "请说普通句子：小朋友你好呀", "请说：小朋友你好呀"),
        PromptSpec("other_speech", "请说普通句子：我想喝一杯水", "请说：我想喝一杯水"),
    ]
    ambient = [
        PromptSpec("ambient", "环境声：保持安静，不说话", "请保持安静，不说话"),
        PromptSpec("ambient", "环境声：轻敲桌面两下", "请轻敲桌面两下"),
        PromptSpec("ambient", "环境声：轻微移动椅子", "请轻微移动椅子"),
        PromptSpec("ambient", "环境声：走动两步", "请走动两步"),
        PromptSpec("ambient", "环境声：翻动书页或纸张", "请翻动书页或纸张"),
    ]

    if group == "near_miss":
        return near_miss
    if group == "other_speech":
        return other_speech
    if group == "ambient":
        return ambient
    return [*near_miss, *other_speech, *ambient]


if __name__ == "__main__":
    main()
