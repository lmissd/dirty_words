"""Wake word interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class WakeEvent:
    """Wake event metadata."""

    wake_word: str


class WakeWordDetector(ABC):
    """Interface for wake word detectors."""

    @abstractmethod
    def wait_for_wake(self) -> WakeEvent:
        """Block until a wake word is detected."""
