from __future__ import annotations

import io
import urllib.error
from typing import Any

import pytest

from nfbench.adapters.ollama_info import OllamaVersionReader


class _Response(io.BytesIO):
    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _opener(body: bytes | None = None, error: Exception | None = None) -> Any:
    def urlopen(url: str, timeout: float) -> _Response:
        assert url == "http://ollama:11434/api/version"
        if error is not None:
            raise error
        return _Response(body or b"")

    return urlopen


def test_version_reader_returns_the_version_field() -> None:
    reader = OllamaVersionReader("http://ollama:11434/", _opener(b'{"version": "0.5.1"}'))

    assert reader() == "0.5.1"


@pytest.mark.parametrize("body", [b"", b"not json", b"[]", b'{"version": 5}', b'{"other": "x"}'])
def test_version_reader_unusable_answer_is_none(body: bytes) -> None:
    assert OllamaVersionReader("http://ollama:11434", _opener(body))() is None


def test_version_reader_server_down_is_none() -> None:
    reader = OllamaVersionReader("http://ollama:11434", _opener(error=urllib.error.URLError("x")))

    assert reader() is None
