"""The version of the Ollama server (its native ``/api/version`` endpoint)."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from nfbench.adapters.http_types import UrlOpen

logger = logging.getLogger(__name__)


class OllamaVersionReader:
    """Callable that returns the server version, or None when it cannot be read."""

    def __init__(
        self, root_url: str, urlopen: UrlOpen = urllib.request.urlopen, timeout_s: float = 5.0
    ) -> None:
        self._url = root_url.rstrip("/") + "/api/version"
        self._urlopen = urlopen
        self._timeout_s = timeout_s

    def __call__(self) -> str | None:
        """The ``version`` field of the answer."""
        try:
            with self._urlopen(self._url, timeout=self._timeout_s) as response:
                version = json.loads(response.read().decode("utf-8")).get("version")
        except (urllib.error.URLError, OSError, ValueError, AttributeError):
            logger.warning("the Ollama version could not be read")
            return None
        return version if isinstance(version, str) else None
