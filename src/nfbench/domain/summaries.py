"""Domain types of the comparison of the summaries that the models wrote (MIL-007)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SummaryEntry:
    """What one model wrote for the hotel analysis in one repetition, with its measurements.

    ``summary`` is None when the answer has none; ``problem`` then says why and ``raw_output``
    holds the text that the model wrote, so the reader can still look at it.
    """

    model: str
    run: int
    summary: str | None
    characters: int
    completion_tokens: int
    tokens_per_s: float | None
    finish_reason: str | None
    valid: bool
    problem: str | None = None
    raw_output: str | None = None

    def to_dict(self) -> dict[str, Any]:  # Any: JSON-shaped payload
        """Plain-dict form for JSON serialisation."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SummaryComparison:
    """The summaries of the models for one repetition of the hotel analysis."""

    run: int | None
    runs: tuple[int, ...]
    entries: tuple[SummaryEntry, ...]
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:  # Any: JSON-shaped payload
        """Plain-dict form for JSON serialisation."""
        return {
            "run": self.run,
            "runs": list(self.runs),
            "entries": [entry.to_dict() for entry in self.entries],
            "message": self.message,
        }
