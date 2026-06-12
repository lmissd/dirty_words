"""Civil language analysis interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from modules.models import CivilityAnalysis


class CivilLanguageAnalyzer(ABC):
    """Interface for text civility analyzers."""

    @abstractmethod
    def analyze(self, text: str) -> CivilityAnalysis:
        """Analyze user text and return structured civility feedback."""
