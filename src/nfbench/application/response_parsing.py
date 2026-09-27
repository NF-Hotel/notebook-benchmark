"""Extract and validate the JSON answer of the hotel analysis. Never raises."""

from __future__ import annotations

import json
import re
from typing import Any

from nfbench.domain.models import ResponseValidation

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_RATE_SECTIONS = ("overall_cancellation", "direct_customers", "agent_bookings")
_LIST_FIELDS = ("key_findings", "limitations")


def extract_json_object(text: str) -> dict[str, Any] | None:  # Any: arbitrary model JSON
    """Best-effort extraction of the first JSON object in ``text``; None if there is none."""
    cleaned = _THINK.sub("", text)
    fenced = _FENCE.search(cleaned)
    if fenced:
        cleaned = fenced.group(1)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        value = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _shape_errors(data: dict[str, Any]) -> list[str]:  # Any: arbitrary model JSON
    errors: list[str] = []
    if not isinstance(data.get("summary"), str):
        errors.append("summary must be a string")
    for name in _RATE_SECTIONS:
        section = data.get(name)
        if not isinstance(section, dict):
            errors.append(f"{name} missing or not an object")
            continue
        if not _is_number(section.get("rate")):
            errors.append(f"{name}.rate must be a number")
        if not isinstance(section.get("interpretation"), str):
            errors.append(f"{name}.interpretation must be a string")
    for name in _LIST_FIELDS:
        items = data.get(name)
        if not isinstance(items, list) or not all(isinstance(i, str) for i in items):
            errors.append(f"{name} must be a list of strings")
    return errors


def validate_hotel_response(text: str) -> ResponseValidation:
    """Check that ``text`` holds the required JSON; keep the parsed data when it does.

    A valid result is a format check only; it says nothing about factual correctness.
    """
    if not text.strip():
        return ResponseValidation(False, None, "empty response")
    data = extract_json_object(text)
    if data is None:
        return ResponseValidation(False, None, "no valid JSON object found")
    errors = _shape_errors(data)
    if errors:
        return ResponseValidation(False, data, "; ".join(errors))
    return ResponseValidation(True, data, None)
