from __future__ import annotations

import json

from nfbench.application.response_parsing import validate_hotel_response

VALID = {
    "summary": "s",
    "overall_cancellation": {"rate": 0.37, "interpretation": "i"},
    "direct_customers": {"rate": 0.3, "interpretation": "i"},
    "agent_bookings": {"rate": 0.4, "interpretation": "i"},
    "key_findings": ["a", "b"],
    "limitations": ["c"],
}


def test_validate_accepts_valid_json() -> None:
    result = validate_hotel_response(json.dumps(VALID))
    assert result.valid
    assert result.data == VALID
    assert result.error is None


def test_validate_accepts_fenced_json_and_think_block() -> None:
    text = f"<think>hmm {{not json}}</think>\n```json\n{json.dumps(VALID)}\n```"
    assert validate_hotel_response(text).valid


def test_validate_rejects_invalid_json_keeps_reason() -> None:
    result = validate_hotel_response("Sure! The rate is 37%.")
    assert not result.valid
    assert result.data is None
    assert result.error == "no valid JSON object found"


def test_validate_rejects_truncated_json() -> None:
    assert not validate_hotel_response(json.dumps(VALID)[:80]).valid


def test_validate_reports_missing_fields_for_incomplete_response() -> None:
    incomplete = {k: v for k, v in VALID.items() if k not in ("agent_bookings", "limitations")}
    result = validate_hotel_response(json.dumps(incomplete))
    assert not result.valid
    assert result.data == incomplete
    assert result.error is not None
    assert "agent_bookings" in result.error
    assert "limitations" in result.error


def test_validate_rejects_boolean_rate() -> None:
    bad = {**VALID, "overall_cancellation": {"rate": True, "interpretation": "i"}}
    assert not validate_hotel_response(json.dumps(bad)).valid


def test_validate_rejects_empty_response() -> None:
    assert validate_hotel_response("  ").error == "empty response"
