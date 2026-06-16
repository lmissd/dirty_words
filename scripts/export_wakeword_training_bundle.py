"""Export wake word training data into a portable bundle."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
import shutil
import sys
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.utils.config_loader import load_config
from modules.utils.disk import ensure_free_space

DEFAULT_SOURCE_DIR = Path("training_data/wakeword")
DEFAULT_OUTPUT_DIR = Path("exports")
DEFAULT_BUNDLE_NAME = "fantuan_fantuan_training_bundle"


@dataclass(frozen=True, slots=True)
class BundleManifest:
    """Summary of the exported training bundle."""

    created_at: str
    wake_phrase: str
    positive_count: int
    negative_count: int
    source_dir: str


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="导出饭团饭团唤醒词训练包。")
    parser.add_argument("--config", default="config/config.yaml", help="配置文件路径。")
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR), help="训练数据源目录。")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="导出目录。")
    parser.add_argument("--bundle-name", default=DEFAULT_BUNDLE_NAME, help="导出包名称。")
    return parser.parse_args()


def main() -> None:
    """Export positive/negative samples and metadata into a zip bundle."""
    args = parse_args()
    config = load_config(Path(args.config))

    source_dir = Path(args.source_dir)
    positive_dir = source_dir / "fantuan_fantuan"
    negative_dir = source_dir / "negative"
    if not positive_dir.exists():
        raise FileNotFoundError(f"未找到正样本目录：{positive_dir}")
    if not negative_dir.exists():
        raise FileNotFoundError(f"未找到负样本目录：{negative_dir}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_free_space(output_dir)

    bundle_dir = output_dir / args.bundle_name
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    copied_positive = copy_wavs(positive_dir, bundle_dir / "positive")
    copied_negative = copy_wavs(negative_dir, bundle_dir / "negative")

    metadata = BundleManifest(
        created_at=datetime.now().isoformat(timespec="seconds"),
        wake_phrase=str(config.get("wakeword.display_wake_word", "饭团饭团")),
        positive_count=copied_positive,
        negative_count=copied_negative,
        source_dir=str(source_dir),
    )

    (bundle_dir / "manifest.json").write_text(
        json.dumps(asdict(metadata), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_csv_snapshot(positive_dir / "metadata.csv", bundle_dir / "positive_metadata.csv")
    write_csv_snapshot(negative_dir / "metadata.csv", bundle_dir / "negative_metadata.csv")

    zip_path = output_dir / f"{args.bundle_name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in bundle_dir.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(bundle_dir))

    print(f"导出完成：{zip_path}")
    print(f"正样本：{copied_positive} 条")
    print(f"负样本：{copied_negative} 条")


def copy_wavs(source_dir: Path, target_dir: Path) -> int:
    """Copy WAV files into a target folder and return count."""
    target_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in sorted(source_dir.rglob("*.wav")):
        shutil.copy2(path, target_dir / path.name)
        count += 1
    return count


def write_csv_snapshot(source: Path, target: Path) -> None:
    """Copy metadata CSV if it exists, otherwise create an empty snapshot."""
    if source.exists():
        shutil.copy2(source, target)
        return

    with target.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["file"])


if __name__ == "__main__":
    main()
