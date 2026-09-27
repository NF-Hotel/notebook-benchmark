from __future__ import annotations

import pytest

from nfbench.application.runner import run_request
from nfbench.domain.models import ChatRequest, StreamChunk
from tests.fakes import FakeBackend, FakeClock

REQUEST = ChatRequest("m1", "hi", 0.0, 64, 5.0)


def test_run_request_measures_ttft_and_rate_from_stream() -> None:
    backend = FakeBackend(
        chunks=[
            StreamChunk(text="thinking", is_reasoning=True),
            StreamChunk(text="answer"),
            StreamChunk(completion_tokens=30, prompt_tokens=8),
        ]
    )
    raw = run_request(backend, REQUEST, FakeClock(0.0, 0.4, 3.4))
    assert raw.text == "answer"  # reasoning is timed but not part of the answer
    assert raw.error is None
    assert raw.metrics.ttft_s == pytest.approx(0.4)
    assert raw.metrics.total_s == pytest.approx(3.4)
    assert raw.metrics.completion_tokens == 30
    assert raw.metrics.prompt_tokens == 8
    assert raw.metrics.tokens_per_s == pytest.approx(10.0)


def test_run_request_backend_error_is_recorded_not_raised() -> None:
    backend = FakeBackend(fail_with="connection refused")
    raw = run_request(backend, REQUEST, FakeClock(0.0, 1.0))
    assert raw.error == "connection refused"
    assert raw.metrics.ttft_s is None
    assert raw.metrics.tokens_per_s is None


def test_run_request_keeps_partial_output_when_stream_fails_midway() -> None:
    backend = FakeBackend(chunks=[StreamChunk(text="par")], fail_with="reset")
    raw = run_request(backend, REQUEST, FakeClock(0.0, 0.1, 0.5))
    assert raw.text == "par"
    assert raw.error == "reset"


def test_run_request_keeps_finish_reason() -> None:
    backend = FakeBackend(chunks=[StreamChunk(text="x"), StreamChunk(finish_reason="stop")])
    raw = run_request(backend, REQUEST, FakeClock(0.0, 0.1, 0.2))
    assert raw.finish_reason == "stop"
