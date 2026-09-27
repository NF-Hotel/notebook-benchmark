"""Benchmark controller: expands a plan into requests, measures, validates, persists."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from nfbench.application.ports import ChatBackend, ResourceMonitor, ResultStore
from nfbench.application.prompts import HOTEL_PROMPT_VERSION, SYSTEM_PROMPT, build_hotel_prompt
from nfbench.application.response_parsing import validate_hotel_response
from nfbench.application.runner import RawRun, run_request
from nfbench.domain.metrics import compute_metrics
from nfbench.domain.models import (
    ANALYSIS_HOTEL,
    ANALYSIS_TASK,
    BenchmarkConfig,
    ChatRequest,
    DatasetInfo,
    HotelSummary,
    ResourceUsage,
    RunResult,
)
from nfbench.domain.tasks import TASKS, Task

logger = logging.getLogger(__name__)

HOTEL_TASK_ID = "hotel-cancellation"
HOTEL_CATEGORY = "analysis"

ProgressCallback = Callable[[int, int, str], None]


@dataclass(frozen=True, slots=True)
class ModelSelection:
    """A model on a backend."""

    backend: str
    model: str


@dataclass(frozen=True, slots=True)
class HotelInput:
    """Dataset identity and its deterministic summary."""

    info: DatasetInfo
    summary: HotelSummary


@dataclass(frozen=True, slots=True)
class _Job:
    selection: ModelSelection
    run: int
    task: Task | None  # None = hotel analysis


class BenchmarkController:
    """Runs the same prompts with the same settings on every selected model."""

    def __init__(
        self,
        backends: Mapping[str, ChatBackend],
        monitor: ResourceMonitor,
        store: ResultStore,
    ) -> None:
        self._backends = backends
        self._monitor = monitor
        self._store = store

    def run(
        self,
        selections: Sequence[ModelSelection],
        config: BenchmarkConfig,
        hotel: HotelInput | None = None,
        progress: ProgressCallback | None = None,
    ) -> list[RunResult]:
        """Execute all jobs; each result is persisted as soon as it exists."""
        jobs = self._plan(selections, config, hotel)
        session_id = uuid.uuid4().hex[:12]
        seen: set[tuple[str, str]] = set()
        results: list[RunResult] = []
        for index, job in enumerate(jobs):
            key = (job.selection.backend, job.selection.model)
            cold = key not in seen
            seen.add(key)
            if progress:
                progress(index, len(jobs), _describe(job))
            result = self._execute(job, config, hotel, session_id, cold)
            self._store.append(result)
            results.append(result)
        if progress:
            progress(len(jobs), len(jobs), "done")
        return results

    @staticmethod
    def _plan(
        selections: Sequence[ModelSelection],
        config: BenchmarkConfig,
        hotel: HotelInput | None,
    ) -> list[_Job]:
        tasks: list[Task | None] = []
        if config.hotel_analysis and hotel is not None:
            tasks.append(None)
        if config.deterministic_tasks:
            tasks.extend(TASKS)
        return [
            _Job(selection, run, task)
            for selection in selections
            for run in range(config.runs)
            for task in tasks
        ]

    def _execute(
        self,
        job: _Job,
        config: BenchmarkConfig,
        hotel: HotelInput | None,
        session_id: str,
        cold: bool,
    ) -> RunResult:
        prompt, system = self._prompt_for(job, hotel)
        request = ChatRequest(
            model=job.selection.model,
            prompt=prompt,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout_s=config.timeout_s,
            system=system,
        )
        timestamp = datetime.now(UTC).isoformat(timespec="seconds")
        backend = self._backends.get(job.selection.backend)
        if backend is None:
            raw = _unavailable(job.selection.backend, request)
            usage = ResourceUsage()
        else:
            self._monitor.start()
            raw = run_request(backend, request)
            usage = self._monitor.stop()
        return _to_result(job, raw, usage, config, hotel, session_id, cold, timestamp)

    @staticmethod
    def _prompt_for(job: _Job, hotel: HotelInput | None) -> tuple[str, str | None]:
        if job.task is not None:
            return job.task.prompt, None
        if hotel is None:
            raise ValueError("hotel analysis requires a HotelInput")
        return build_hotel_prompt(hotel.summary), SYSTEM_PROMPT


def _describe(job: _Job) -> str:
    what = HOTEL_TASK_ID if job.task is None else job.task.id
    return f"{job.selection.backend}/{job.selection.model} - {what} (run {job.run + 1})"


def _unavailable(backend: str, request: ChatRequest) -> RawRun:
    metrics = compute_metrics(0.0, None, 0.0, None, 0)
    return RawRun("", metrics, f"backend '{backend}' is not configured for {request.model}")


def _to_result(
    job: _Job,
    raw: RawRun,
    usage: ResourceUsage,
    config: BenchmarkConfig,
    hotel: HotelInput | None,
    session_id: str,
    cold: bool,
    timestamp: str,
) -> RunResult:
    is_hotel = job.task is None
    passed: bool | None = None
    valid: bool | None = None
    validation_error: str | None = None
    if raw.error is None:
        if job.task is not None and job.task.check is not None:
            passed = job.task.check(raw.text)
        if is_hotel:
            validation = validate_hotel_response(raw.text)
            valid, validation_error = validation.valid, validation.error
            if not validation.valid and raw.finish_reason == "length":
                validation_error = f"{validation_error} (output cut off at max_tokens)"
    if raw.error:
        logger.warning("%s failed: %s", _describe(job), raw.error)
    info = hotel.info if hotel is not None and is_hotel else None
    return RunResult(
        backend=job.selection.backend,
        model=job.selection.model,
        task_id=HOTEL_TASK_ID if job.task is None else job.task.id,
        category=HOTEL_CATEGORY if job.task is None else job.task.category,
        run=job.run,
        cold=cold,
        ttft_s=raw.metrics.ttft_s,
        total_s=raw.metrics.total_s,
        completion_tokens=raw.metrics.completion_tokens,
        prompt_tokens=raw.metrics.prompt_tokens,
        tokens_per_s=raw.metrics.tokens_per_s,
        tokens_estimated=raw.metrics.tokens_estimated,
        passed=passed,
        output=raw.text,
        error=raw.error,
        analysis_type=ANALYSIS_HOTEL if is_hotel else ANALYSIS_TASK,
        session_id=session_id,
        timestamp=timestamp,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        runs=config.runs,
        prompt_version=HOTEL_PROMPT_VERSION if is_hotel else None,
        dataset=info.name if info else None,
        dataset_hash=info.sha256 if info else None,
        dataset_rows=info.rows if info else None,
        resources=usage,
        response_valid=valid,
        validation_error=validation_error,
        finish_reason=raw.finish_reason,
    )
