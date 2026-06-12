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

    @abstractmethod
    def show_result(self, user_text: str, analysis: CivilityAnalysis) -> None:
        """Show the analysis result."""

    @abstractmethod
    def show_error(self, message: str) -> None:
        """Show a recoverable error."""
