from __future__ import annotations

import json
from typing import Any

from nfbench.application.summary_comparison import (
    NO_HOTEL_ANALYSIS,
    UNKNOWN_REPETITION,
    compare_summaries,
)
from nfbench.domain.models import ANALYSIS_HOTEL, ANALYSIS_TASK

ANSWER = {
    "summary": "Cancellations are high.",
    "overall_cancellation": {"rate": 0.37, "interpretation": "i"},
    "direct_customers": {"rate": 0.3, "interpretation": "i"},
    "agent_bookings": {"rate": 0.4, "interpretation": "i"},
    "key_findings": ["a"],
    "limitations": ["b"],
}


def record(model: str, output: str, run: int = 1, **changes: Any) -> dict[str, Any]:  # Any: record
    base: dict[str, Any] = {
        "model": model,
        "run": run,
        "analysis_type": ANALYSIS_HOTEL,
        "output": output,
        "completion_tokens": 120,
        "tokens_per_s": 30.5,
        "finish_reason": "stop",
        "error": None,
    }
    base.update(changes)
    return base


def answer(summary: str) -> str:
    return json.dumps({**ANSWER, "summary": summary})


def test_one_entry_per_model_with_the_stored_summary() -> None:
    records = [
        record("a:1b", answer("First.")),
        record("b:2b", answer("Second.")),
        record("c:3b", answer("Third.")),
    ]
    comparison = compare_summaries(records)
    assert comparison.message is None
    assert comparison.run == 1
    assert [(e.model, e.summary) for e in comparison.entries] == [
        ("a:1b", "First."),
        ("b:2b", "Second."),
        ("c:3b", "Third."),
    ]
    first = comparison.entries[0]
    assert first.valid
    assert first.characters == len(records[0]["output"])
    assert first.completion_tokens == 120
    assert first.tokens_per_s == 30.5
    assert first.finish_reason == "stop"
    assert first.problem is None
    assert first.raw_output is None


def test_answer_cut_off_at_max_tokens_has_no_summary_and_keeps_the_raw_text() -> None:
    cut = record("a:1b", '{"summary": "Cancel', finish_reason="length")
    entry = compare_summaries([cut]).entries[0]
    assert entry.summary is None
    assert not entry.valid
    assert entry.problem == "cut off at the maximum output tokens"
    assert entry.raw_output == '{"summary": "Cancel'


def test_a_length_finish_wins_even_when_the_text_parses() -> None:
    entry = compare_summaries([record("a:1b", answer("Ok."), finish_reason="length")]).entries[0]
    assert entry.summary is None
    assert entry.problem == "cut off at the maximum output tokens"


def test_answer_that_is_not_json_says_why_and_shows_the_raw_text() -> None:
    entry = compare_summaries([record("a:1b", "The rate is 37%.")]).entries[0]
    assert entry.summary is None
    assert not entry.valid
    assert entry.problem == "no valid JSON object found"
    assert entry.raw_output == "The rate is 37%."


def test_answer_with_the_wrong_shape_has_no_summary() -> None:
    entry = compare_summaries([record("a:1b", json.dumps({"summary": "Only this."}))]).entries[0]
    assert entry.summary is None
    assert entry.problem is not None
    assert "overall_cancellation" in entry.problem


def test_empty_answer_is_not_an_error() -> None:
    entry = compare_summaries([record("a:1b", "", error="timeout")]).entries[0]
    assert entry.summary is None
    assert entry.characters == 0
    assert entry.problem == "empty response"


def test_the_first_repetition_is_read_by_default_and_another_can_be_asked_for() -> None:
    records = [
        record("a:1b", answer("One."), run=1),
        record("a:1b", answer("Two."), run=2),
        record("b:2b", answer("Other one."), run=1),
        record("b:2b", answer("Other two."), run=2),
    ]
    first = compare_summaries(records)
    assert first.run == 1
    assert first.runs == (1, 2)
    assert [e.summary for e in first.entries] == ["One.", "Other one."]
    second = compare_summaries(records, run=2)
    assert second.run == 2
    assert [e.summary for e in second.entries] == ["Two.", "Other two."]


def test_a_repetition_that_does_not_exist_gives_a_message() -> None:
    comparison = compare_summaries([record("a:1b", answer("One."))], run=7)
    assert comparison.entries == ()
    assert comparison.runs == (1,)
    assert comparison.message == UNKNOWN_REPETITION


def test_a_result_without_hotel_analysis_gives_an_empty_comparison_and_a_message() -> None:
    task = record("a:1b", "42", analysis_type=ANALYSIS_TASK)
    for records in ([], [task]):
        comparison = compare_summaries(records)
        assert comparison.entries == ()
        assert comparison.run is None
        assert comparison.message == NO_HOTEL_ANALYSIS


def test_deterministic_task_records_are_left_out() -> None:
    records = [record("a:1b", "42", analysis_type=ANALYSIS_TASK), record("a:1b", answer("S."))]
    assert [e.summary for e in compare_summaries(records).entries] == ["S."]


def test_the_comparison_is_json_shaped() -> None:
    comparison = compare_summaries([record("a:1b", answer("S."))])
    body = json.loads(json.dumps(comparison.to_dict()))
    assert body["run"] == 1
    assert body["runs"] == [1]
    assert body["message"] is None
    assert body["entries"][0]["summary"] == "S."
