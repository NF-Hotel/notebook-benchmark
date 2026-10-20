"""Fakes of the service ports (no mocks, no network, no sleeping)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from nfbench.application.benchmark import HotelInput
from nfbench.application.ports import Payload
from nfbench.domain.errors import BackendError, ModelInUseError
from nfbench.domain.models import (
    BenchmarkConfig,
    DatasetInfo,
    GroupStats,
    HotelSummary,
    RunResult,
)
from nfbench.domain.service import BackendInfo, DeliveryOutcome, MachineInfo

INFO = DatasetInfo("d.csv", "/x/d.csv", "a" * 64, 10, ("a",), {"a": "Int64"}, {"a": 0})
SUMMARY = HotelSummary(GroupStats(10, 5, 0.5), GroupStats(5, 2, 0.4), GroupStats(5, 3, 0.6))
HOTEL = HotelInput(INFO, SUMMARY)
MACHINE = MachineInfo("Test CPU", 4, 8192, None, "Linux")
BACKEND = BackendInfo("ollama", "0.5.1")


def make_result(
    model: str = "m1",
    run: int = 0,
    cold: bool = True,
    output: str = "{}",
    finish_reason: str | None = None,
) -> RunResult:
    """A finished request with the fields of schema version 2."""
    return RunResult(
        backend="ollama",
        model=model,
        task_id="hotel-cancellation",
        category="analysis",
        run=run,
        cold=cold,
        ttft_s=0.5,
        total_s=2.0,
        completion_tokens=10,
        prompt_tokens=20,
        tokens_per_s=5.0,
        tokens_estimated=False,
        passed=None,
        output=output,
        error=None,
        analysis_type="hotel_cancellation",
        session_id="s1",
        timestamp="2026-10-19T10:00:00+00:00",
        temperature=0.0,
        max_tokens=2048,
        runs=1,
        prompt_version="hotel-v1",
        dataset="d.csv",
        dataset_hash="a" * 64,
        dataset_rows=10,
        response_valid=True,
        finish_reason=finish_reason,
    )


class FakeCatalog:
    """Lists scripted installed models."""

    def __init__(self, *models: str) -> None:
        self.models = models

    def installed_models(self) -> tuple[str, ...]:
        return self.models


class FakeModelAdmin:
    """Pulls into and deletes from a ``FakeCatalog``, or fails as scripted."""

    def __init__(self, catalog: FakeCatalog) -> None:
        self._catalog = catalog
        self.pulled: list[str] = []
        self.deleted: list[str] = []
        self.fail_with: str | None = None
        self.progress_before_failing: int | None = None
        self.defect: Exception | None = None
        self.delete_result = True
        self.delete_error: Exception | None = None

    def pull(self, model: str, on_progress: Callable[[int | None], None]) -> None:
        self.pulled.append(model)
        if self.defect is not None:
            raise self.defect
        if self.progress_before_failing is not None:
            on_progress(self.progress_before_failing)
        if self.fail_with is not None:
            raise BackendError(self.fail_with)
        on_progress(50)
        self._catalog.models = (*self._catalog.models, model)

    def delete(self, model: str) -> bool:
        if self.delete_error is not None:
            raise self.delete_error
        if self.delete_result:
            self.deleted.append(model)
            self._catalog.models = tuple(m for m in self._catalog.models if m != model)
        return self.delete_result


class FakeGuard:
    """A model use guard: models in ``in_use`` are refused, any other is deleted."""

    def __init__(self, in_use: set[str] | None = None) -> None:
        self.in_use = in_use or set()
        self.checked: list[str] = []

    def delete_if_unused(self, model: str, delete: Callable[[], bool]) -> bool:
        if model in self.in_use:
            raise ModelInUseError(model)
        self.checked.append(model)
        return delete()


class FakeInspector:
    """Returns a fixed machine and backend."""

    def machine(self) -> MachineInfo:
        return MACHINE

    def backend(self) -> BackendInfo:
        return BACKEND


class FakeExecutor:
    """Returns one result per selected model, or raises."""

    def __init__(
        self,
        fail_with: str | None = None,
        answers: dict[str, tuple[str, str | None]] | None = None,
    ) -> None:
        self.fail_with = fail_with
        self.answers = answers or {}  # model -> (output, finish_reason)
        self.calls: list[tuple[list[str], BenchmarkConfig]] = []

    def run(
        self, selections: Sequence[Any], config: BenchmarkConfig, hotel: Any | None = None
    ) -> list[RunResult]:
        models = [s.model for s in selections]
        self.calls.append((models, config))
        if self.fail_with:
            raise RuntimeError(self.fail_with)
        return [
            make_result(model, output=out, finish_reason=reason)
            for model in models
            for out, reason in [self.answers.get(model, ("{}", None))]
        ]


class FakeSender:
    """Answers with scripted outcomes (the last one repeats) and records the payloads."""

    def __init__(self, *outcomes: DeliveryOutcome) -> None:
        self.outcomes = list(outcomes) or [DeliveryOutcome.DELIVERED]
        self.sent: list[Payload] = []

    def send(self, payload: Payload) -> DeliveryOutcome:
        self.sent.append(payload)
        return self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]


class MemoryPendingStore:
    """Keeps unsent results in a dict and records how they ended."""

    def __init__(self) -> None:
        self.items: dict[str, Payload] = {}
        self.delivered: list[str] = []
        self.failed: list[str] = []

    def save(self, run_id: str, payload: Payload) -> None:
        self.items[run_id] = payload

    def pending(self) -> list[tuple[str, Payload]]:
        done = {*self.delivered, *self.failed}
        return [(rid, body) for rid, body in self.items.items() if rid not in done]

    def mark_delivered(self, run_id: str) -> None:
        self.delivered.append(run_id)

    def mark_failed(self, run_id: str) -> None:
        self.failed.append(run_id)

    def find(self, run_id: str) -> Payload | None:
        return self.items.get(run_id)


class FakeEpoch:
    """A clock in seconds since the epoch that the test moves by hand."""

    def __init__(self, now: float) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now
