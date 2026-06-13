"""Full-screen robot animation display for wake-greeting mode."""

from __future__ import annotations

import logging
from pathlib import Path
import time

from modules.display.base import Display
from modules.models import CivilityAnalysis
from modules.utils.config_loader import AppConfig
from modules.utils.errors import DisplayError

LOGGER = logging.getLogger(__name__)


class RobotAnimationDisplay(Display):
    """Render the Fantuan robot animation on an HDMI screen."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        try:
            import tkinter as tk
        except ImportError as exc:
            raise DisplayError("当前系统缺少 tkinter，无法启用机器人动画显示。") from exc

        self.tk = tk
        self.background = str(config.get("robot_animation.background_color", "#f7f3e8"))
        self.text_color = str(config.get("robot_animation.text_color", "#1d2b2a"))
        self.font_family = str(config.get("display.font_family", "Noto Sans CJK SC"))
        self.font_size = int(config.get("robot_animation.font_size", config.get("display.font_size", 36)))
        self.duration_seconds = float(config.get("robot_animation.duration_seconds", 2.0))
        self.frame_delay_seconds = float(config.get("robot_animation.frame_delay_seconds", 0.0))
        self.final_frame = int(config.get("robot_animation.final_frame", 7))

        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            raise DisplayError("无法打开机器人动画窗口，请确认已连接 HDMI 屏幕并在桌面环境中运行。") from exc
        self.root.title(str(config.get("app.name", "文明用语机器人")))
        self.root.configure(bg=self.background)
        self.root.attributes("-fullscreen", bool(config.get("display.fullscreen", True)))
        self.root.bind("<Escape>", lambda _event: self.root.attributes("-fullscreen", False))

        self.canvas = tk.Canvas(self.root, bg=self.background, highlightthickness=0)
        self.canvas.pack(expand=True, fill="both")
        self.root.update_idletasks()
        self.root.update()

        self.frames = self._load_frames()
        self.current_image_id: int | None = None
        self.current_text_id: int | None = None

    def show_standby(self, wake_words: list[str]) -> None:
        wake_text = "、".join(wake_words) if wake_words else "未配置"
        self._show_frame(self._safe_final_frame(), f"待机中\n请说：{wake_text}")

    def show_status(self, message: str) -> None:
        self._show_frame(self._safe_final_frame(), message)

    def show_wake_success(self, wake_word: str) -> None:
        LOGGER.info("播放机器人唤醒动画：%s", wake_word)
        if not self.frames:
            self.show_status(f"唤醒成功：{wake_word}")
            return

        frame_count = len(self.frames)
        delay = self.frame_delay_seconds or max(0.05, self.duration_seconds / frame_count)
        started = time.monotonic()
        index = 0

        while time.monotonic() - started < self.duration_seconds:
            self._show_frame(index % frame_count, "小朋友你好")
            time.sleep(delay)
            index += 1

        self._show_frame(self._safe_final_frame(), "小朋友你好")

    def show_greeting_complete(self) -> None:
        LOGGER.info("问候完成，保持机器人微笑画面。")
        self._show_frame(self._safe_final_frame(), "小朋友你好")

    def show_result(self, user_text: str, analysis: CivilityAnalysis) -> None:
        status = "文明表达" if analysis.civilized else "需要改进"
        self._show_frame(
            self._safe_final_frame(),
            "\n".join([status, f"评分：{analysis.score}/100", analysis.suggestion]),
        )

    def show_error(self, message: str) -> None:
        self._show_frame(self._safe_final_frame(), f"系统提示\n{message}")

    def _load_frames(self) -> list:
        frame_dir = Path(str(self.config.get("robot_animation.frame_dir", "assets/robot/fantuan_jump")))
        paths = sorted(frame_dir.glob("frame_*.png"))
        if not paths:
            raise DisplayError(f"机器人动画帧不存在：{frame_dir}")
        return [self.tk.PhotoImage(file=str(path)) for path in paths]

    def _show_frame(self, frame_index: int, text: str) -> None:
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        frame = self.frames[frame_index]

        image_y = int(height * 0.45)
        text_y = min(height - 70, image_y + frame.height() // 2 + 64)
        self.current_image_id = self.canvas.create_image(width // 2, image_y, image=frame)
        self.current_text_id = self.canvas.create_text(
            width // 2,
            text_y,
            text=text,
            fill=self.text_color,
            font=(self.font_family, self.font_size, "bold"),
            justify="center",
        )
        self.root.update_idletasks()
        self.root.update()

    def _safe_final_frame(self) -> int:
        if not self.frames:
            return 0
        return min(max(0, self.final_frame), len(self.frames) - 1)
