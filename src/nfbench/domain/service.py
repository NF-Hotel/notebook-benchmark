"""Domain types of the benchmark service: the state of a run and its delivery (ADR-0001)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

MAX_MODELS = 4
MAX_RUNS = 5
MAX_WAITING_RUNS = 2
DELIVERY_WINDOW_S = 15 * 60
FIRST_RETRY_DELAY_S = 5.0


class RunState(StrEnum):
    """Where a run is in its life."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class DeliveryState(StrEnum):
    """Where the result of a run is on its way to the web API."""

    NOT_READY = "not_ready"
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"


class DeliveryOutcome(StrEnum):
    """What one attempt to send a result came to."""

    DELIVERED = "delivered"
    RETRY = "retry"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class StartRunRequest:
    """What an administrator asks for: the models and the options of the notebook."""

    models: tuple[str, ...]
    hotel_analysis: bool = True
    deterministic_tasks: bool = False
    runs: int = 1


@dataclass(frozen=True, slots=True)
class RunStatus:
    """The state of one run as the API shows it."""

    run_id: str
    state: RunState
    delivery: DeliveryState
    models: tuple[str, ...]
    queued_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class MachineInfo:
    """The machine a run was made on; ``gpu`` is None for a run on the CPU only."""

    cpu: str
    cpu_cores: int
    memory_mb: int
    gpu: str | None
    os: str


@dataclass(frozen=True, slots=True)
class BackendInfo:
    """The model server a run used."""

    name: str
    version: str | None
