"""Entry point for Civil Language Robot."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from modules.app import build_app, run_wakeword_test
from modules.utils.errors import RobotError


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="文明用语机器人")
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to config.yaml. Defaults to config/config.yaml.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one wake-record-analyze cycle and exit.",
    )
    parser.add_argument(
        "--wakeword-only",
        action="store_true",
        help="Only test wake word detection and exit after one wake event.",
    )
    return parser.parse_args()


def main() -> int:
    """Start the robot app."""
    args = parse_args()

    try:
        if args.wakeword_only:
            run_wakeword_test(Path(args.config))
            return 0

        app = build_app(Path(args.config))
        if args.once:
            app.run_once()
        else:
            app.run_forever()
        return 0
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("收到退出信号，正在关闭。")
        return 0
    except RobotError as exc:
        logging.getLogger(__name__).error("机器人启动失败：%s", exc)
        print(f"启动失败：{exc}", file=sys.stderr)
        return 2
    except Exception:
        logging.getLogger(__name__).exception("发生未处理异常。")
        print("发生未处理异常，请查看 logs/robot.log。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
