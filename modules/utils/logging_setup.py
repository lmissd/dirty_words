"""Logging setup."""

from __future__ import annotations

import logging
from pathlib import Path

from modules.utils.config_loader import AppConfig


def setup_logging(config: AppConfig) -> None:
    """Configure console and file logging."""
    logs_dir = Path(str(config.get("paths.logs_dir", "logs")))
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "robot.log"

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
