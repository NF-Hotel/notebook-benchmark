"""Pull and delete models with the native API of Ollama (ADR-0005)."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable

from nfbench.adapters.http_types import UrlOpen
from nfbench.domain.errors import BackendError

logger = logging.getLogger(__name__)

PULL_READ_TIMEOUT_S = 600.0
DELETE_TIMEOUT_S = 60.0
_JSON = {"Content-Type": "application/json"}


class OllamaModelAdmin:
    """Calls Ollama; every failure is a ``BackendError`` with a reason a person can read."""

    def __init__(
        self,
        root_url: str,
        urlopen: UrlOpen = urllib.request.urlopen,
        pull_timeout_s: float = PULL_READ_TIMEOUT_S,
        delete_timeout_s: float = DELETE_TIMEOUT_S,
    ) -> None:
        self._root = root_url.rstrip("/")
        self._urlopen = urlopen
        self._pull_timeout_s = pull_timeout_s
        self._delete_timeout_s = delete_timeout_s

    def pull(self, model: str, on_progress: Callable[[int | None], None]) -> None:
        """Stream ``/api/pull``; the last line must say ``success``."""
        body = json.dumps({"model": model, "stream": True}).encode("utf-8")
        request = urllib.request.Request(
            self._root + "/api/pull", data=body, headers=_JSON, method="POST"
        )
        succeeded = False
        try:
            with self._urlopen(request, timeout=self._pull_timeout_s) as response:
                for raw in response:
                    line = _parse_line(raw)
                    if line is None:
                        continue
                    if isinstance(line.get("error"), str):
                        raise BackendError(line["error"])
                    on_progress(_percent(line))
                    succeeded = line.get("status") == "success"
        except urllib.error.HTTPError as error:
            raise BackendError(_http_reason(error)) from error
        except (urllib.error.URLError, OSError) as error:
            raise BackendError(f"Ollama could not be reached: {error}") from error
        if not succeeded:
            raise BackendError("Ollama ended the pull without saying that it succeeded")

    def delete(self, model: str) -> bool:
        """``DELETE /api/delete``; Ollama answers 404 for a model that is not installed."""
        body = json.dumps({"model": model}).encode("utf-8")
        request = urllib.request.Request(
            self._root + "/api/delete", data=body, headers=_JSON, method="DELETE"
        )
        try:
            with self._urlopen(request, timeout=self._delete_timeout_s):
                return True
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return False
            raise BackendError(_http_reason(error)) from error
        except (urllib.error.URLError, OSError) as error:
            raise BackendError(f"Ollama could not be reached: {error}") from error


def _parse_line(raw: bytes | str) -> dict[str, object] | None:
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
    text = text.strip()
    if not text:
        return None
    try:
        value = json.loads(text)
    except ValueError:
        logger.warning("an unreadable line from the Ollama pull was skipped")
        return None
    return value if isinstance(value, dict) else None


def _percent(line: dict[str, object]) -> int | None:
    total, completed = line.get("total"), line.get("completed")
    if (
        isinstance(total, int)
        and isinstance(completed, int)
        and not isinstance(total, bool)
        and total > 0
    ):
        return max(0, min(99, completed * 100 // total))
    return None


def _http_reason(error: urllib.error.HTTPError) -> str:
    try:
        message = json.loads(error.read().decode("utf-8", "replace")).get("error")
    except (ValueError, AttributeError, OSError):
        message = None
    return message if isinstance(message, str) and message else f"Ollama answered {error.code}"
