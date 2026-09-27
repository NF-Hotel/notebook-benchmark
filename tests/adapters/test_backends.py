from __future__ import annotations

import json

import pytest

from nfbench.adapters.backends import OpenAICompatibleBackend, default_backends, parse_sse_line
from nfbench.domain.errors import BackendError
from nfbench.domain.models import ChatRequest


def _event(payload: dict[str, object]) -> str:
    return "data: " + json.dumps(payload)


def test_parse_sse_line_extracts_content() -> None:
    (chunk,) = parse_sse_line(_event({"choices": [{"delta": {"content": "hi"}}]}))
    assert chunk.text == "hi"
    assert not chunk.is_reasoning


@pytest.mark.parametrize("key", ["reasoning_content", "reasoning"])
def test_parse_sse_line_marks_reasoning_from_both_servers(key: str) -> None:
    (chunk,) = parse_sse_line(_event({"choices": [{"delta": {key: "hmm"}}]}))
    assert chunk.text == "hmm"
    assert chunk.is_reasoning


def test_parse_sse_line_reads_usage_event() -> None:
    (chunk,) = parse_sse_line(
        _event({"choices": [], "usage": {"completion_tokens": 5, "prompt_tokens": 9}})
    )
    assert (chunk.completion_tokens, chunk.prompt_tokens) == (5, 9)


def test_parse_sse_line_ignores_done_blank_and_non_data_lines() -> None:
    assert parse_sse_line("data: [DONE]") == []
    assert parse_sse_line("") == []
    assert parse_sse_line(": keep-alive") == []


def test_parse_sse_line_error_object_raises_backend_error() -> None:
    with pytest.raises(BackendError, match="server error"):
        parse_sse_line(_event({"error": {"message": "model not found"}}))


def test_parse_sse_line_malformed_json_raises_backend_error() -> None:
    with pytest.raises(BackendError, match="malformed"):
        parse_sse_line("data: {oops")


def test_check_unreachable_backend_returns_unavailable_status_without_raising() -> None:
    status = OpenAICompatibleBackend("ollama", "http://127.0.0.1:9/v1").check(timeout=0.5)
    assert not status.available
    assert status.models == ()
    assert status.error


def test_stream_chat_unreachable_backend_raises_backend_error() -> None:
    backend = OpenAICompatibleBackend("ollama", "http://127.0.0.1:9/v1")
    request = ChatRequest("m", "hi", 0.0, 8, 0.5)
    with pytest.raises(BackendError):
        list(backend.stream_chat(request))


def test_default_backends_use_documented_urls() -> None:
    backends = default_backends()
    assert backends["ollama"].base_url == "http://localhost:11434/v1"
    assert backends["lmstudio"].base_url == "http://localhost:1234/v1"


@pytest.mark.integration
def test_live_backends_report_status_without_raising() -> None:
    for backend in default_backends().values():
        status = backend.check()
        assert status.available == bool(status.models) or status.error is None


def test_parse_sse_line_reports_finish_reason() -> None:
    chunks = parse_sse_line(_event({"choices": [{"delta": {}, "finish_reason": "length"}]}))
    assert [c.finish_reason for c in chunks] == ["length"]
