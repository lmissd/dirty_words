"""Tkinter full-screen display for Raspberry Pi HDMI screens."""

from __future__ import annotations

import logging
import time

from modules.display.base import Display
from modules.models import CivilityAnalysis
from modules.utils.config_loader import AppConfig
from modules.utils.errors import DisplayError

LOGGER = logging.getLogger(__name__)


class TkinterDisplay(Display):
    """Render large Chinese text on a full-screen HDMI display."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        try:
            import tkinter as tk
        except ImportError as exc:
            raise DisplayError("当前系统缺少 tkinter，无法启用全屏显示。") from exc

        self.tk = tk
        self.root = tk.Tk()
        self.root.title(str(config.get("app.name", "文明用语机器人")))
        self.root.configure(bg="#f7f3e8")
        self.root.attributes("-fullscreen", bool(config.get("display.fullscreen", True)))
        self.root.bind("<Escape>", lambda _event: self.root.attributes("-fullscreen", False))

        font_family = str(config.get("display.font_family", "Noto Sans CJK SC"))
        font_size = int(config.get("display.font_size", 36))
        self.label = tk.Label(
            self.root,
            text="",
            bg="#f7f3e8",
            fg="#1d2b2a",
            font=(font_family, font_size),
            justify="left",
            wraplength=1000,
            padx=64,
            pady=64,
        )
        self.label.pack(expand=True, fill="both")
        self.root.update()

    def show_standby(self, wake_words: list[str]) -> None:
        wake_text = "、".join(wake_words) if wake_words else "未配置"
        self._render(f"待机中\n\n请说：{wake_text}")

    def show_status(self, message: str) -> None:
        self._render(message)

    def show_result(self, user_text: str, analysis: CivilityAnalysis) -> None:
        status = "文明表达" if analysis.civilized else "需要改进"
        self._render(
            "\n".join(
                [
                    "文明用语分析",
                    "",
                    f"用户原话：{user_text}",
                    f"结果：{status}",
                    f"文明评分：{analysis.score}/100",
                    f"原因：{analysis.reason}",
                    f"建议：{analysis.suggestion}",
                ]
            )
        )
        time.sleep(float(self.config.get("display.result_hold_seconds", 8)))

    def show_error(self, message: str) -> None:
        self._render(f"系统提示\n\n{message}")

    def _render(self, text: str) -> None:
        LOGGER.info("屏幕显示：%s", text)
        self.label.config(text=text)
        self.root.update_idletasks()
        self.root.update()
