"""Shared domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CivilityAnalysis:
    """Structured result returned by the civil language analyzer."""

    civilized: bool
    score: int
    reason: str
    suggestion: str
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CivilityAnalysis":
        """Create an analysis object from a JSON-like dictionary."""
        score = _clamp_score(data.get("score", 0))
        return cls(
            civilized=_to_bool(data.get("civilized", False)),
            score=score,
            reason=str(data.get("reason") or "未提供原因"),
            suggestion=str(data.get("suggestion") or "请尝试使用更加尊重、温和的表达方式。"),
            raw=data,
        )


def _clamp_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = 0
    return max(0, min(100, score))


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "是", "文明"}
    return bool(value)
