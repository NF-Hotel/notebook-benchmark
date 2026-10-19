from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from nfbench.adapters.ollama_models import OllamaModelAdmin
from nfbench.domain.errors import BackendError

ROOT = "http://ollama:11434"


class _Response(io.BytesIO):
    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _lines(*items: object) -> bytes:
    return b"".join(
        (json.dumps(i) if not isinstance(i, str) else i).encode() + b"\n" for i in items
    )


class _Opener:
    """A urlopen that records the request and answers a scripted body or raises."""

    def __init__(self, body: bytes = b"", error: Exception | None = None) -> None:
        self.body = body
        self.error = error
        self.request: urllib.request.Request | None = None
        self.timeout: float | None = None

    def __call__(self, request: urllib.request.Request, timeout: float) -> _Response:
        self.request = request
        self.timeout = timeout
        if self.error is not None:
            raise self.error
        return _Response(self.body)


def _http_error(code: int, body: bytes = b"") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(ROOT, code, "x", {}, io.BytesIO(body))  # type: ignore[arg-type]


def _admin(opener: _Opener) -> OllamaModelAdmin:
    return OllamaModelAdmin(ROOT + "/", urlopen=opener, pull_timeout_s=7.0, delete_timeout_s=3.0)


def test_pull_posts_the_model_to_api_pull_and_streams() -> None:
    opener = _Opener(_lines({"status": "success"}))

    _admin(opener).pull("phi4-mini", lambda percent: None)

    assert opener.request is not None
    assert (opener.request.get_method(), opener.request.full_url) == ("POST", ROOT + "/api/pull")
    assert json.loads(opener.request.data) == {"model": "phi4-mini", "stream": True}  # type: ignore[arg-type]
    assert opener.timeout == 7.0


def test_pull_reports_the_percent_of_the_bytes_and_never_a_hundred_before_success() -> None:
    seen: list[int | None] = []
    body = _lines(
        {"status": "pulling manifest"},
        {"status": "pulling abc", "total": 200, "completed": 50},
        {"status": "pulling abc", "total": 200, "completed": 200},
        {"status": "success"},
    )

    _admin(_Opener(body)).pull("m", seen.append)

    assert seen == [None, 25, 99, None]


@pytest.mark.parametrize("line", [{"total": 0, "completed": 0}, {"total": True, "completed": 1}])
def test_pull_a_line_without_a_usable_total_has_no_percent(line: dict[str, Any]) -> None:
    seen: list[int | None] = []

    _admin(_Opener(_lines(line, {"status": "success"}))).pull("m", seen.append)

    assert seen == [None, None]


def test_pull_an_error_line_raises_with_the_reason() -> None:
    body = _lines(
        {"status": "pulling manifest"}, {"error": "pull model manifest: file does not exist"}
    )

    with pytest.raises(BackendError, match="file does not exist"):
        _admin(_Opener(body)).pull("nope", lambda percent: None)


def test_pull_an_unreadable_or_blank_line_is_skipped() -> None:
    seen: list[int | None] = []
    body = b"\nnot json\n[1, 2]\n" + _lines({"status": "success"})

    _admin(_Opener(body)).pull("m", seen.append)

    assert seen == [None]


def test_pull_that_ends_without_success_raises() -> None:
    with pytest.raises(BackendError, match="without saying that it succeeded"):
        _admin(_Opener(_lines({"status": "pulling abc", "total": 10, "completed": 5}))).pull(
            "m", lambda percent: None
        )


def test_pull_an_http_error_raises_with_the_message_of_ollama() -> None:
    opener = _Opener(error=_http_error(500, b'{"error": "no space left on device"}'))

    with pytest.raises(BackendError, match="no space left on device"):
        _admin(opener).pull("m", lambda percent: None)


def test_pull_an_http_error_without_a_message_names_the_status() -> None:
    with pytest.raises(BackendError, match="Ollama answered 503"):
        _admin(_Opener(error=_http_error(503, b"<html>"))).pull("m", lambda percent: None)


def test_pull_when_ollama_cannot_be_reached_raises() -> None:
    opener = _Opener(error=urllib.error.URLError("connection refused"))

    with pytest.raises(BackendError, match="could not be reached"):
        _admin(opener).pull("m", lambda percent: None)


def test_delete_sends_delete_with_the_model_in_the_body() -> None:
    opener = _Opener(b"")

    assert _admin(opener).delete("phi4-mini:latest") is True

    assert opener.request is not None
    assert (opener.request.get_method(), opener.request.full_url) == (
        "DELETE",
        ROOT + "/api/delete",
    )
    assert json.loads(opener.request.data) == {"model": "phi4-mini:latest"}  # type: ignore[arg-type]
    assert opener.timeout == 3.0


def test_delete_a_model_that_is_not_installed_is_false() -> None:
    assert (
        _admin(_Opener(error=_http_error(404, b'{"error": "model not found"}'))).delete("m")
        is False
    )


def test_delete_another_http_error_raises() -> None:
    with pytest.raises(BackendError, match="Ollama answered 500"):
        _admin(_Opener(error=_http_error(500))).delete("m")


def test_delete_when_ollama_cannot_be_reached_raises() -> None:
    with pytest.raises(BackendError, match="could not be reached"):
        _admin(_Opener(error=urllib.error.URLError("down"))).delete("m")
