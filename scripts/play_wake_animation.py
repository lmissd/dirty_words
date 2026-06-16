"""Preview the robot wake animation on an HDMI display."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.utils.config_loader import load_config


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="播放一次小机器人唤醒动画。")
    parser.add_argument("--config", default="config/config.yaml", help="配置文件路径。")
    parser.add_argument("--text", default=None, help="动画下方显示的文字，默认读取 greeting.text。")
    parser.add_argument("--duration", type=float, default=None, help="覆盖动画播放时长，单位秒。")
    parser.add_argument("--hold-seconds", type=float, default=2.0, help="动画结束后停留时长。")
    parser.add_argument("--windowed", action="store_true", help="用窗口模式预览，不进入全屏。")
    return parser.parse_args()


def main() -> None:
    """Play the configured robot wake animation once."""
    args = parse_args()
    config = load_config(Path(args.config))

    try:
        import tkinter as tk
    except ImportError as exc:
        raise SystemExit("当前系统缺少 tkinter，无法播放动画。") from exc

    root = tk.Tk()
    try:
        background = str(config.get("robot_animation.background_color", "#f7f3e8"))
        text_color = str(config.get("robot_animation.text_color", "#1d2b2a"))
        font_family = str(config.get("display.font_family", "Noto Sans CJK SC"))
        font_size = int(config.get("robot_animation.font_size", config.get("display.font_size", 36)))
        duration_seconds = float(
            args.duration
            if args.duration is not None
            else config.get("robot_animation.duration_seconds", 2.0)
        )
        frame_delay_seconds = float(config.get("robot_animation.frame_delay_seconds", 0.0))
        final_frame = int(config.get("robot_animation.final_frame", 7))
        display_text = args.text or str(config.get("greeting.text", "小朋友你好"))

        root.title("小机器人唤醒动画预览")
        root.configure(bg=background)
        root.attributes("-fullscreen", not args.windowed and bool(config.get("display.fullscreen", True)))
        root.bind("<Escape>", lambda _event: root.attributes("-fullscreen", False))

        canvas = tk.Canvas(root, bg=background, highlightthickness=0)
        canvas.pack(expand=True, fill="both")
        root.update_idletasks()
        root.update()

        frame_dir = _resolve_frame_dir(config.path, str(config.get("robot_animation.frame_dir", "assets/robot/fantuan_jump")))
        frame_paths = sorted(frame_dir.glob("frame_*.png"))
        if not frame_paths:
            raise SystemExit(f"机器人动画帧不存在：{frame_dir}")

        frames = [tk.PhotoImage(file=str(path)) for path in frame_paths]
        delay = frame_delay_seconds or max(0.05, duration_seconds / len(frames))
        started = time.monotonic()
        index = 0

        while time.monotonic() - started < duration_seconds:
            _show_frame(canvas, frames[index % len(frames)], display_text, text_color, font_family, font_size)
            time.sleep(delay)
            index += 1

        final_index = min(max(0, final_frame), len(frames) - 1)
        _show_frame(canvas, frames[final_index], display_text, text_color, font_family, font_size)
        if args.hold_seconds > 0:
            time.sleep(args.hold_seconds)
    finally:
        root.destroy()


def _resolve_frame_dir(config_path: Path, frame_dir_text: str) -> Path:
    frame_dir = Path(frame_dir_text)
    if frame_dir.is_absolute():
        return frame_dir

    resolved_config_path = config_path.resolve()
    if resolved_config_path.parent.name == "config":
        return resolved_config_path.parent.parent / frame_dir
    return PROJECT_ROOT / frame_dir


def _show_frame(
    canvas,
    frame,
    text: str,
    text_color: str,
    font_family: str,
    font_size: int,
) -> None:
    canvas.delete("all")
    width = max(1, canvas.winfo_width())
    height = max(1, canvas.winfo_height())
    image_y = int(height * 0.45)
    text_y = min(height - 70, image_y + frame.height() // 2 + 64)
    canvas.create_image(width // 2, image_y, image=frame)
    canvas.create_text(
        width // 2,
        text_y,
        text=text,
        fill=text_color,
        font=(font_family, font_size, "bold"),
        justify="center",
    )
    canvas.update_idletasks()
    canvas.update()


if __name__ == "__main__":
    main()
