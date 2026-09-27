"""Deterministic benchmark prompts. `check` is an optional callable for a cheap pass/fail."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Task:
    """A short prompt with an optional automatic check of the answer."""

    id: str
    category: str
    prompt: str
    check: Callable[[str], bool] | None = None


TASKS: tuple[Task, ...] = (
    Task(
        "math-1",
        "reasoning",
        "A train leaves at 09:15 and arrives at 11:50. How many minutes is the trip? "
        "Answer with just the number.",
        lambda o: "155" in o,
    ),
    Task(
        "logic-1",
        "reasoning",
        "If all bloops are razzies and all razzies are lazzies, are all bloops lazzies? "
        "Answer yes or no.",
        lambda o: "yes" in o.lower(),
    ),
    Task(
        "code-1",
        "coding",
        "Write a Python function is_palindrome(s) ignoring case and non-alphanumerics. Code only.",
        lambda o: "def is_palindrome" in o,
    ),
    Task(
        "extract-1",
        "extraction",
        'Return only JSON with keys "name" and "city" from: "Anna Berg moved to Oslo in 2019."',
        lambda o: "Anna" in o and "Oslo" in o,
    ),
    Task(
        "summ-1",
        "summarization",
        "Summarize in one sentence: Local LLM servers let teams run models on their own "
        "hardware, trading some speed and quality for privacy, cost control and offline use.",
    ),
)
