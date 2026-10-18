"""Types shared by the HTTP adapters."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

UrlOpen = Callable[..., Any]  # Any: urllib.request.urlopen returns an http.client response
