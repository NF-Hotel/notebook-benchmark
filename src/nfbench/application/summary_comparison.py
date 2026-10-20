"""Compare the summaries that the models wrote for the hotel analysis (MIL-007). Never raises."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from nfbench.application.response_parsing import validate_hotel_response
from nfbench.domain.models import ANALYSIS_HOTEL
from nfbench.domain.summaries import SummaryComparison, SummaryEntry

NO_HOTEL_ANALYSIS = "There is no hotel analysis to compare in this result."
UNKNOWN_REPETITION = "This result has no such repetition."
_CUT_OFF = "cut off at the maximum output tokens"
_LENGTH = "length"

# Any: a record is the JSON-shaped result of one request (the result schema of the notebook and
# the payload of the service).
Record = Mapping[str, Any]


def compare_summaries(records: Sequence[Record], run: int | None = None) -> SummaryComparison:
    """One entry per model for one repetition of the hotel analysis, in the order of the records.

    ``run`` is the repetition to read; the first one that the records have when it is None.
    """
    hotel = [record for record in records if record.get("analysis_type") == ANALYSIS_HOTEL]
    runs = tuple(sorted({int(record["run"]) for record in hotel}))
    if not runs:
        return SummaryComparison(None, (), (), NO_HOTEL_ANALYSIS)
    chosen = runs[0] if run is None else run
    if chosen not in runs:
        return SummaryComparison(None, runs, (), UNKNOWN_REPETITION)
    entries = tuple(_entry(record) for record in hotel if int(record["run"]) == chosen)
    return SummaryComparison(chosen, runs, entries)


def _entry(record: Record) -> SummaryEntry:
    output = str(record.get("output") or "")
    finish_reason = record.get("finish_reason")
    summary: str | None = None
    problem: str | None = None
    if finish_reason == _LENGTH:
        problem = _CUT_OFF
    else:
        validation = validate_hotel_response(output)
        summary = _summary_of(validation.data) if validation.valid else None
        if summary is None:
            problem = validation.error or record.get("error") or "no summary in the answer"
    return SummaryEntry(
        model=str(record["model"]),
        run=int(record["run"]),
        summary=summary,
        characters=len(output),
        completion_tokens=int(record.get("completion_tokens") or 0),
        tokens_per_s=record.get("tokens_per_s"),
        finish_reason=finish_reason,
        valid=summary is not None,
        problem=None if problem is None else str(problem),
        raw_output=output if summary is None else None,
    )


def _summary_of(data: Mapping[str, Any] | None) -> str | None:  # Any: arbitrary model JSON
    value = None if data is None else data.get("summary")
    return value if isinstance(value, str) and value.strip() else None
