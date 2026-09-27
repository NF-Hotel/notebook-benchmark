"""Prompt for the hotel cancellation analysis. Only deterministic statistics are sent."""

from __future__ import annotations

import json

from nfbench.domain.models import HotelSummary

HOTEL_PROMPT_VERSION = "hotel-cancellation-v1"

SYSTEM_PROMPT = (
    "You are a careful data analyst. Use only the statistics supplied by the user. "
    "Do not invent values that are not present in the supplied data. "
    "Correlation is not causation. Answer with a single JSON object and nothing else."
)

_RESPONSE_SHAPE = {
    "summary": "string",
    "overall_cancellation": {"rate": "number between 0 and 1", "interpretation": "string"},
    "direct_customers": {"rate": "number between 0 and 1", "interpretation": "string"},
    "agent_bookings": {"rate": "number between 0 and 1", "interpretation": "string"},
    "key_findings": ["string"],
    "limitations": ["string"],
}

_INSTRUCTIONS = """\
Below are cancellation statistics of a hotel-booking dataset, calculated with Python.
"Direct" bookings have no booking agent; "agent" bookings were made through an agent.
Rates are fractions (0.25 = 25%).

Tasks:
1. Explain the overall cancellation rate.
2. Compare direct customers and agent bookings and identify meaningful differences.
3. Identify patterns and which variables appear associated with cancellations.
4. Do not claim causation where the data only shows correlation.
5. State uncertainty and limitations (e.g. small groups, missing dimensions).
6. Base every conclusion on the supplied statistics only.

Respond with JSON of exactly this shape:
"""


def build_hotel_prompt(summary: HotelSummary) -> str:
    """User prompt containing the statistics as JSON and the required answer shape."""
    stats = json.dumps(summary.to_dict(), indent=1, sort_keys=True)
    shape = json.dumps(_RESPONSE_SHAPE, indent=1)
    return f"{_INSTRUCTIONS}{shape}\n\nSTATISTICS:\n{stats}\n"
