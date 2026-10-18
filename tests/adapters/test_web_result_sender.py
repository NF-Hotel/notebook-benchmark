from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from nfbench.adapters.web_result_sender import WebResultSender
from nfbench.domain.service import DeliveryOutcome


class _Response:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _Opener:
    """Stands in for ``urllib.request.urlopen``: answers a status, or raises."""

    def __init__(self, status: int | None = 201, error: Exception | None = None) -> None:
        self.status = status
        self.error = error
        self.requests: list[urllib.request.Request] = []

    def __call__(self, request: urllib.request.Request, timeout: float) -> _Response:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        assert self.status is not None
        return _Response(self.status)


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://web/x", code, "x", {}, io.BytesIO(b""))  # type: ignore[arg-type]


def _sender(opener: _Opener) -> WebResultSender:
    return WebResultSender("http://api:8080/", "tok", urlopen=opener)


PAYLOAD: dict[str, Any] = {"run_id": "r1", "results": []}


@pytest.mark.parametrize("status", [200, 201])
def test_send_created_or_repeat_is_delivered(status: int) -> None:
    assert _sender(_Opener(status)).send(PAYLOAD) is DeliveryOutcome.DELIVERED


def test_send_posts_json_to_the_results_path_with_the_bearer_token() -> None:
    opener = _Opener(201)

    _sender(opener).send(PAYLOAD)

    (request,) = opener.requests
    assert request.full_url == "http://api:8080/api/benchmark/results"
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "Bearer tok"
    assert request.get_header("Content-type") == "application/json"
    assert json.loads(request.data) == PAYLOAD  # type: ignore[arg-type]


@pytest.mark.parametrize("code", [400, 401, 403, 404, 413, 422])
def test_send_client_error_is_rejected_and_not_retried(code: int) -> None:
    sender = _sender(_Opener(error=_http_error(code)))

    assert sender.send(PAYLOAD) is DeliveryOutcome.REJECTED


@pytest.mark.parametrize("code", [408, 429, 500, 502, 503])
def test_send_server_error_or_throttle_is_retried(code: int) -> None:
    sender = _sender(_Opener(error=_http_error(code)))

    assert sender.send(PAYLOAD) is DeliveryOutcome.RETRY


@pytest.mark.parametrize(
    "error", [urllib.error.URLError("refused"), TimeoutError("slow"), ConnectionResetError()]
)
def test_send_no_answer_is_retried(error: Exception) -> None:
    assert _sender(_Opener(error=error)).send(PAYLOAD) is DeliveryOutcome.RETRY


def test_send_unexpected_status_is_retried() -> None:
    assert _sender(_Opener(status=302)).send(PAYLOAD) is DeliveryOutcome.RETRY
