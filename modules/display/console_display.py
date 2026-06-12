"""Console display implementation."""

from __future__ import annotations

import logging

from modules.display.base import Display
from modules.models import CivilityAnalysis
from modules.utils.config_loader import AppConfig

LOGGER = logging.getLogger(__name__)


class ConsoleDisplay(Display):
    """Print robot state to the console."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def show_standby(self, wake_words: list[str]) -> None:
        text = "、".join(wake_words) if wake_words else "未配置"
        self._print(f"待机中。请说或输入唤醒词：{text}")

    def show_status(self, message: str) -> None:
        self._print(message)

    def show_result(self, user_text: str, analysis: CivilityAnalysis) -> None:
        status = "文明表达" if analysis.civilized else "需要改进"
        self._print(
            "\n".join(
                [
                    "分析完成",
                    f"用户原话：{user_text}",
                    f"结果：{status}",
                    f"文明评分：{analysis.score}/100",
                    f"原因：{analysis.reason}",
                    f"建议：{analysis.suggestion}",
                ]
            )
        )

    def show_error(self, message: str) -> None:
        self._print(f"错误：{message}")

    def _print(self, message: str) -> None:
        LOGGER.info("显示：%s", message)
        print(f"\n[文明用语机器人] {message}\n")
