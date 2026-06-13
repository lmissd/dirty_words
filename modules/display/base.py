"""Display interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from modules.models import CivilityAnalysis


class Display(ABC):
    """Interface for screen output."""

    @abstractmethod
    def show_standby(self, wake_words: list[str]) -> None:
        """Show standby state."""

    @abstractmethod
    def show_status(self, message: str) -> None:
        """Show a transient status message."""

    def show_wake_success(self, wake_word: str) -> None:
        """Show a wake success event."""
        self.show_status(f"唤醒成功：{wake_word}")

    def show_greeting_complete(self) -> None:
        """Show that the wake greeting has completed."""
        self.show_status("问候完成，返回待机。")

    @abstractmethod
    def show_result(self, user_text: str, analysis: CivilityAnalysis) -> None:
        """Show the analysis result."""

    @abstractmethod
    def show_error(self, message: str) -> None:
        """Show a recoverable error."""
