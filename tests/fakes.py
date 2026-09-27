"""Fakes of the application ports (no mocks, no network)."""

from __future__ import annotations

from collections.abc import Iterator

from nfbench.domain.errors import BackendError
from nfbench.domain.models import (
    BackendStatus,
    ChatRequest,
    ResourceUsage,
    RunResult,
    StreamChunk,
)


class FakeClock:
    """Returns the scripted times one by one."""

    def __init__(self, *times: float) -> None:
        self._times = iter(times)

    def __call__(self) -> float:
        return next(self._times)


class FakeBackend:
    """Streams scripted chunks, then optionally fails."""

    def __init__(
        self,
        name: str = "fake",
        chunks: list[StreamChunk] | None = None,
        fail_with: str | None = None,
    ) -> None:
        self._name = name
        self.chunks = chunks or []
        self.fail_with = fail_with
        self.requests: list[ChatRequest] = []

    @property
    def name(self) -> str:
        return self._name

    def check(self) -> BackendStatus:
        return BackendStatus(self._name, "fake://", True, ("m1",))

    def stream_chat(self, request: ChatRequest) -> Iterator[StreamChunk]:
        self.requests.append(request)
        yield from self.chunks
        if self.fail_with:
            raise BackendError(self.fail_with)


class FakeMonitor:
    """Returns a fixed usage; counts calls."""

    def __init__(self, usage: ResourceUsage | None = None) -> None:
        self.usage = usage or ResourceUsage(1.0, 2.0, 3.0, None, None, None)
        self.starts = 0

    def start(self) -> None:
        self.starts += 1

    def stop(self) -> ResourceUsage:
        return self.usage


class MemoryStore:
    """Keeps results in a list."""

    def __init__(self) -> None:
        self.results: list[RunResult] = []

    def append(self, result: RunResult) -> None:
        self.results.append(result)
