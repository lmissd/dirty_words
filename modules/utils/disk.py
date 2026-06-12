"""Disk space helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

from modules.utils.errors import StorageError


def ensure_free_space(path: Path, minimum_mb: int = 100) -> None:
    """Raise if the target filesystem has too little free space."""
    path.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(path)
    free_mb = usage.free / 1024 / 1024
    if free_mb < minimum_mb:
        raise StorageError(f"SD 卡剩余空间不足：{free_mb:.1f} MB，小于 {minimum_mb} MB")
