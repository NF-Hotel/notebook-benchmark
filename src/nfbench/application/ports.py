"""Ports: the narrow interfaces the application layer needs from the outside world."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import Any, Protocol

from nfbench.domain.models import (
    BackendStatus,
    BenchmarkConfig,
    ChatRequest,
    ResourceUsage,
    RunResult,
    StreamChunk,
)
from nfbench.domain.service import BackendInfo, DeliveryOutcome, MachineInfo

Payload = Mapping[
    str, Any
]  # Any: JSON-shaped body of the contract (openapi/benchmark-contract.yaml)


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


class ModelCatalog(Protocol):
    """The models that are installed in the model server."""

    def installed_models(self) -> tuple[str, ...]:
        """Names as the server lists them; empty when the server is down."""
        ...


class ModelAdmin(Protocol):
    """Pulls models into the model server and deletes them (ADR-0005)."""

    def pull(self, model: str, on_progress: Callable[[int | None], None]) -> None:
        """Pull a model, reporting the percent of the bytes (None before a total is known).

        Raise ``BackendError`` with the reason when the server cannot pull it.
        """
        ...

    def delete(self, model: str) -> bool:
        """Delete an installed model: True when deleted, False when it is not installed."""
        ...


class ModelUseGuard(Protocol):
    """Lets a delete run while no queued or running run names the model (ADR-0005)."""

    def delete_if_unused(self, model: str, delete: Callable[[], bool]) -> bool:
        """Call ``delete`` under the run lock; raise ``ModelInUseError`` if a run uses the model."""
        ...


class MachineInspector(Protocol):
    """Describes the machine and the model server for the result header."""

    def machine(self) -> MachineInfo:
        """CPU, memory, GPU or none, and the operating system."""
        ...

    def backend(self) -> BackendInfo:
        """Name and version of the model server (version None when unknown)."""
        ...


class ResultSender(Protocol):
    """Sends a finished result to the web API."""

    def send(self, payload: Payload) -> DeliveryOutcome:
        """One attempt; never raises. RETRY = try again later, REJECTED = a defect (400 or 401)."""
        ...


class PendingResultStore(Protocol):
    """Keeps finished results until the web API has them."""

    def save(self, run_id: str, payload: Payload) -> None:
        """Write the result before the first attempt to send it."""
        ...

    def pending(self) -> list[tuple[str, Payload]]:
        """All results that are neither delivered nor failed."""
        ...

    def mark_delivered(self, run_id: str) -> None:
        """The web API has the result."""
        ...

    def mark_failed(self, run_id: str) -> None:
        """Give up sending; the result stays available for a manual send."""
        ...


class BenchmarkExecutor(Protocol):
    """Runs the models through the benchmark use case."""

    def run(
        self, selections: Sequence[Any], config: BenchmarkConfig, hotel: Any | None = None
    ) -> list[RunResult]:
        """Execute all requests and return their results."""
        ...
