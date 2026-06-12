"""Download the small Chinese Vosk model used for offline wake detection."""

from __future__ import annotations

import urllib.request
import zipfile
from pathlib import Path

MODEL_NAME = "vosk-model-small-cn-0.22"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"
MODELS_DIR = Path("models")
MODEL_DIR = MODELS_DIR / MODEL_NAME
ZIP_PATH = MODELS_DIR / f"{MODEL_NAME}.zip"


def main() -> None:
    """Download and extract the Vosk Chinese model if it is missing."""
    if MODEL_DIR.exists():
        print(f"Vosk model already exists: {MODEL_DIR}")
        return

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {MODEL_URL}")
    urllib.request.urlretrieve(MODEL_URL, ZIP_PATH)

    print(f"Extracting {ZIP_PATH}")
    with zipfile.ZipFile(ZIP_PATH, "r") as archive:
        archive.extractall(MODELS_DIR)

    ZIP_PATH.unlink(missing_ok=True)

    if not MODEL_DIR.exists():
        raise RuntimeError(f"Expected model directory was not created: {MODEL_DIR}")

    print(f"Vosk model ready: {MODEL_DIR}")
    print(f"Approximate size: {_format_size(_directory_size(MODEL_DIR))}")


def _directory_size(path: Path) -> int:
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def _format_size(size_bytes: int) -> str:
    size_mb = size_bytes / 1024 / 1024
    return f"{size_mb:.1f} MB"


if __name__ == "__main__":
    main()
