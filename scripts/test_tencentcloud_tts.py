"""Minimal Tencent Cloud TTS test for Raspberry Pi."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.app import _build_tts
from modules.utils.audio_player import AudioPlayer
from modules.utils.config_loader import load_config
from modules.utils.errors import RobotError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Minimal Tencent Cloud TTS test.")
    parser.add_argument("--config", default="config/config.yaml", help="Path to config file.")
    parser.add_argument(
        "--text",
        default="\u5c0f\u670b\u53cb\u4f60\u597d\uff0c\u6211\u662f\u996d\u56e2\u673a\u5668\u4eba\u3002",
        help="Text to synthesize.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(Path(args.config))
    tts = _build_tts(config, AudioPlayer(config))
    try:
        output = tts.speak(args.text)
        print("Tencent Cloud TTS success.")
        if output is not None:
            print(f"Output audio: {output}")
        return 0
    except RobotError as exc:
        print(f"Tencent Cloud TTS failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
