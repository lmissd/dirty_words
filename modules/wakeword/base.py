"""Wake word interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable


@dataclass(slots=True)
class WakeEvent:
    """Wake event metadata."""

    wake_word: str


class WakeWordDetector(ABC):
    """Interface for wake word detectors."""

    @abstractmethod
    def wait_for_wake(self, on_ready: Callable[[], None] | None = None) -> WakeEvent:
        """Block until a wake word is detected.

        The optional ``on_ready`` callback is invoked once the detector has
        finished setup and is genuinely ready to listen for the wake phrase.
        """
