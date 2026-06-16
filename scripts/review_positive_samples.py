"""Review positive wake word samples and relabel noisy clips."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.utils.config_loader import load_config
from modules.utils.disk import ensure_free_space

POSITIVE_DIR = Path("training_data/wakeword/fantuan_fantuan")
NEGATIVE_DIR = Path("training_data/wakeword/negative/review_noise")


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="逐条复听正样本，并把噪音样本转移到负样本目录。")
    parser.add_argument("--config", default="config/config.yaml", help="配置文件路径。")
    parser.add_argument("--positive-dir", default=str(POSITIVE_DIR), help="正样本目录。")
    parser.add_argument("--negative-dir", default=str(NEGATIVE_DIR), help="噪音样本转移目录。")
    parser.add_argument("--start", type=int, default=1, help="从第几条开始复听，默认 1。")
    return parser.parse_args()


def main() -> None:
    """Review positive samples interactively."""
    args = parse_args()
    config = load_config(Path(args.config))

    from modules.utils.audio_player import AudioPlayer
    from modules.utils.errors import AudioOutputError

    positive_dir = Path(args.positive_dir)
    negative_dir = Path(args.negative_dir)
    positive_dir.mkdir(parents=True, exist_ok=True)
    negative_dir.mkdir(parents=True, exist_ok=True)
    ensure_free_space(negative_dir)

    samples = sorted(positive_dir.glob("fantuan_fantuan_*.wav"))
    if not samples:
        print(f"没有找到正样本：{positive_dir}")
        return

    start_index = max(1, args.start)
    current = start_index - 1
    player = AudioPlayer(config)

    print("=== 正样本复听筛查 ===")
    print(f"正样本目录：{positive_dir}")
    print(f"噪音转移目录：{negative_dir}")
    print("操作：k=保留，n=噪音并转到负样本，r=重播，q=退出")

    while current < len(samples):
        samples = sorted(positive_dir.glob("fantuan_fantuan_*.wav"))
        if current >= len(samples):
            break

        sample = samples[current]
        print(f"\n第 {current + 1}/{len(samples)} 条：{sample.name}")
        while True:
            try:
                player.play(sample)
            except AudioOutputError as exc:
                print(f"播放失败：{exc}")
                return

            action = input("输入 k 保留，n 标记为噪音，r 重播，q 退出。\n> ").strip().lower()
            if action in {"", "k"}:
                current += 1
                break
            if action == "r":
                continue
            if action == "n":
                target = move_to_negative(sample, negative_dir)
                print(f"已转移到负样本：{target}")
                rebuild_positive_metadata(positive_dir)
                append_negative_metadata(negative_dir, target)
                break
            if action == "q":
                rebuild_positive_metadata(positive_dir)
                print("已退出复听。")
                return
            print("请输入 k、n、r 或 q。")

    rebuild_positive_metadata(positive_dir)
    print("复听完成，正样本 metadata 已更新。")


def move_to_negative(sample: Path, negative_dir: Path) -> Path:
    """Move one positive sample into the review-noise negative directory."""
    target = negative_dir / sample.name.replace("fantuan_fantuan_", "review_noise_")
    counter = 1
    while target.exists():
        target = negative_dir / f"{sample.stem}_noise_{counter:02d}{sample.suffix}"
        counter += 1
    shutil.move(str(sample), str(target))
    return target


def rebuild_positive_metadata(positive_dir: Path) -> None:
    """Rebuild metadata.csv from remaining positive WAV files."""
    metadata_path = positive_dir / "metadata.csv"
    rows = [
        {
            "file": path.name,
            "phrase": "饭团饭团",
            "sample_rate": "48000",
            "channels": "1",
            "duration_seconds": "2.000",
            "created_at": "",
        }
        for path in sorted(positive_dir.glob("fantuan_fantuan_*.wav"))
    ]
    with metadata_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["file", "phrase", "sample_rate", "channels", "duration_seconds", "created_at"],
        )
        writer.writeheader()
        writer.writerows(rows)


def append_negative_metadata(negative_dir: Path, sample: Path) -> None:
    """Append one relabeled noise sample to negative metadata.csv."""
    metadata_path = negative_dir.parent / "metadata.csv"
    rows = []
    if metadata_path.exists():
        with metadata_path.open("r", newline="", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))

    relative_file = sample.relative_to(negative_dir.parent).as_posix()
    rows.append(
        {
            "file": relative_file,
            "category": "review_noise",
            "prompt_text": "从正样本复听中转移的噪音/无效样本",
            "sample_rate": "48000",
            "channels": "1",
            "duration_seconds": "2.000",
            "created_at": "",
        }
    )

    with metadata_path.open("w", newline="", encoding="utf-8") as file:
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
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
