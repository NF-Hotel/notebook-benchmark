"""Ports: the narrow interfaces the application layer needs from the outside world."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from nfbench.domain.models import BackendStatus, ChatRequest, ResourceUsage, RunResult, StreamChunk


class ChatBackend(Protocol):
    """A model server that streams chat completions."""

    @property
    def name(self) -> str:
        """Backend identifier."""
        ...

    def check(self) -> BackendStatus:
        """Report connectivity and models; must not raise."""
        ...

    def stream_chat(self, request: ChatRequest) -> Iterator[StreamChunk]:
        """Yield decoded chunks; raise ``BackendError`` on transport or server errors."""
        ...


class ResourceMonitor(Protocol):
    """Samples RAM / VRAM between ``start`` and ``stop``."""

    def start(self) -> None:
        """Take the 'before' sample and begin peak tracking."""
        ...

    def stop(self) -> ResourceUsage:
        """Take the 'after' sample and return before / after / peak."""
        ...


class ResultStore(Protocol):
    """Persists results."""

    def append(self, result: RunResult) -> None:
        """Persist one result immediately."""
        ...
