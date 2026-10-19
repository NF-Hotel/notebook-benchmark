"""The runs of the benchmark service: start, queue, run one at a time, hand over to delivery."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from nfbench.application.benchmark import HotelInput, ModelSelection
from nfbench.application.delivery import DeliveryService
from nfbench.application.payload import build_result_payload
from nfbench.application.ports import BenchmarkExecutor, MachineInspector, ModelCatalog
from nfbench.domain.errors import (
    InvalidRunRequestError,
    ModelInUseError,
    ModelNotInstalledError,
    QueueFullError,
    RunNotFoundError,
)
from nfbench.domain.models import BenchmarkConfig
from nfbench.domain.service import (
    MAX_MODELS,
    MAX_RUNS,
    MAX_WAITING_RUNS,
    DeliveryState,
    RunState,
    RunStatus,
    StartRunRequest,
)

logger = logging.getLogger(__name__)

BACKEND_NAME = "ollama"


@dataclass(frozen=True, slots=True)
class _Queued:
    run_id: str
    request: StartRunRequest


class RunService:
    """Takes start requests, runs them one at a time and gives each result to the delivery."""

    def __init__(
        self,
        catalog: ModelCatalog,
        executor: BenchmarkExecutor,
        hotel_provider: Callable[[], HotelInput],
        inspector: MachineInspector,
        delivery: DeliveryService,
        clock: Callable[[], float] = time.time,
        new_id: Callable[[], str] = lambda: str(uuid.uuid4()),
    ) -> None:
        self._catalog = catalog
        self._executor = executor
        self._hotel_provider = hotel_provider
        self._inspector = inspector
        self._delivery = delivery
        self._clock = clock
        self._new_id = new_id
        self._lock = threading.Lock()
        self._statuses: dict[str, RunStatus] = {}
        self._waiting: deque[_Queued] = deque()

    def installed_models(self) -> tuple[str, ...]:
        """The models that a run may name."""
        return self._catalog.installed_models()

    def start(self, request: StartRunRequest) -> RunStatus:
        """Queue a run; raise when the request is invalid or the queue is full."""
        self._validate(request)
        with self._lock:
            if len(self._waiting) >= MAX_WAITING_RUNS:
                raise QueueFullError("a run is active and the queue is full")
            # Checked under the lock that delete_if_unused takes, so a model cannot be deleted
            # between this check and the queuing (ADR-0005).
            self._require_installed(request.models)
            run_id = self._new_id()
            status = RunStatus(
                run_id,
                RunState.QUEUED,
                DeliveryState.NOT_READY,
                request.models,
                self._now(),
            )
            self._statuses[run_id] = status
            self._waiting.append(_Queued(run_id, request))
            return status

    def status(self, run_id: str) -> RunStatus:
        """The state of a run."""
        with self._lock:
            try:
                return self._statuses[run_id]
            except KeyError as error:
                raise RunNotFoundError(run_id) from error

    def restore(self) -> None:
        """Pick up results that were not delivered before a restart."""
        self._delivery.restore()

    def tick(self) -> bool:
        """Make the due delivery attempts, then run the oldest queued run; True if work was done."""
        ended = self._delivery.deliver_due()
        for run_id, state in ended.items():
            self._set(run_id, delivery=state)
        return self._run_next() or bool(ended)

    def _validate(self, request: StartRunRequest) -> None:
        models = request.models
        if not 1 <= len(models) <= MAX_MODELS:
            raise InvalidRunRequestError(f"choose 1 to {MAX_MODELS} models")
        if len(set(models)) != len(models):
            raise InvalidRunRequestError("a model is named twice")
        if not 1 <= request.runs <= MAX_RUNS:
            raise InvalidRunRequestError(f"runs must be 1 to {MAX_RUNS}")
        if not (request.hotel_analysis or request.deterministic_tasks):
            raise InvalidRunRequestError("choose at least one analysis")

    def _require_installed(self, models: tuple[str, ...]) -> None:
        installed = set(self._catalog.installed_models())
        for model in models:
            if model not in installed:
                raise ModelNotInstalledError(f"model '{model}' is not installed")

    def delete_if_unused(self, model: str, delete: Callable[[], bool]) -> bool:
        """Call ``delete`` while no queued or running run names the model (ADR-0005)."""
        with self._lock:
            for status in self._statuses.values():
                if status.state in (RunState.QUEUED, RunState.RUNNING) and model in status.models:
                    raise ModelInUseError(f"model '{model}' is used by run {status.run_id}")
            return delete()

    def _run_next(self) -> bool:
        with self._lock:
            if not self._waiting:
                return False
            queued = self._waiting.popleft()
        started = self._now()
        self._set(queued.run_id, state=RunState.RUNNING, started_at=started)
        try:
            payload = self._execute(queued, started)
        except Exception as error:
            logger.exception("run %s failed", queued.run_id)
            self._set(
                queued.run_id, state=RunState.FAILED, finished_at=self._now(), error=str(error)
            )
            return True
        self._delivery.submit(payload)
        self._set(
            queued.run_id,
            state=RunState.DONE,
            delivery=DeliveryState.PENDING,
            finished_at=str(payload["finished_at"]),
        )
        return True

    def _execute(self, queued: _Queued, started_at: str) -> dict[str, object]:
        request = queued.request
        hotel = self._hotel_provider()
        config = BenchmarkConfig(
            runs=request.runs,
            hotel_analysis=request.hotel_analysis,
            deterministic_tasks=request.deterministic_tasks,
        )
        selections = [ModelSelection(BACKEND_NAME, model) for model in request.models]
        results = self._executor.run(selections, config, hotel)
        return build_result_payload(
            queued.run_id,
            started_at,
            self._now(),
            results,
            hotel,
            self._inspector.machine(),
            self._inspector.backend(),
        )

    def _set(self, run_id: str, **changes: object) -> None:
        with self._lock:
            current = self._statuses.get(run_id)
            if current is not None:
                self._statuses[run_id] = replace(current, **changes)  # type: ignore[arg-type]

    def _now(self) -> str:
        return datetime.fromtimestamp(self._clock(), UTC).isoformat(timespec="seconds")
