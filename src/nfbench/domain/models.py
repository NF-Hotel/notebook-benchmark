"""Domain models: frozen value objects shared by all layers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = 2
ANALYSIS_HOTEL = "hotel_cancellation"
ANALYSIS_TASK = "deterministic_task"


@dataclass(frozen=True, slots=True)
class BackendStatus:
    """Connectivity result for one model server; ``available`` False carries the reason."""

    name: str
    base_url: str
    available: bool
    models: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True, slots=True)
class BenchmarkConfig:
    """Settings applied identically to every model in a session."""

    temperature: float = 0.0
    max_tokens: int = 2048
    runs: int = 1
    timeout_s: float = 600.0
    hotel_analysis: bool = True
    deterministic_tasks: bool = False


@dataclass(frozen=True, slots=True)
class ChatRequest:
    """One prompt for one model."""

    model: str
    prompt: str
    temperature: float
    max_tokens: int
    timeout_s: float
    system: str | None = None


@dataclass(frozen=True, slots=True)
class StreamChunk:
    """One decoded streaming event; usage fields are set on the event that carries them."""

    text: str = ""
    is_reasoning: bool = False
    completion_tokens: int | None = None
    prompt_tokens: int | None = None
    finish_reason: str | None = None


@dataclass(frozen=True, slots=True)
class RunMetrics:
    """Performance figures of one request (see BENCHMARK_METHODOLOGY.md)."""

    ttft_s: float | None
    total_s: float
    completion_tokens: int
    prompt_tokens: int | None
    tokens_per_s: float | None
    tokens_estimated: bool


@dataclass(frozen=True, slots=True)
class ResourceUsage:
    """RAM / VRAM in MB before, after and at peak; None = not measurable."""

    ram_before_mb: float | None = None
    ram_after_mb: float | None = None
    ram_peak_mb: float | None = None
    vram_before_mb: float | None = None
    vram_after_mb: float | None = None
    vram_peak_mb: float | None = None


@dataclass(frozen=True, slots=True)
class ColumnMapping:
    """Which dataset columns play which role. Optional roles set to None are skipped."""

    canceled: str = "is_canceled"
    agent: str = "agent"
    categorical: tuple[str, ...] = (
        "hotel",
        "market_segment",
        "distribution_channel",
        "deposit_type",
        "customer_type",
    )
    lead_time: str | None = "lead_time"
    adr: str | None = "adr"
    booking_changes: str | None = "booking_changes"
    previous_cancellations: str | None = "previous_cancellations"
    special_requests: str | None = "total_of_special_requests"
    arrival_month: str | None = "arrival_date_month"


@dataclass(frozen=True, slots=True)
class DatasetInfo:
    """Identity and shape of a loaded CSV."""

    name: str
    path: str
    sha256: str
    rows: int
    columns: tuple[str, ...]
    dtypes: dict[str, str]
    missing: dict[str, int]


@dataclass(frozen=True, slots=True)
class GroupStats:
    """Bookings and cancellations of one group; rate is None for an empty group."""

    bookings: int
    cancellations: int
    rate: float | None


@dataclass(frozen=True, slots=True)
class BreakdownRow:
    """Cancellation statistics of one value of a dimension."""

    value: str
    stats: GroupStats


@dataclass(frozen=True, slots=True)
class Breakdown:
    """Cancellation statistics per value of one dimension (largest groups first)."""

    dimension: str
    rows: tuple[BreakdownRow, ...]
    omitted_groups: int = 0


@dataclass(frozen=True, slots=True)
class HotelSummary:
    """Deterministic facts computed from the dataset; the only data the LLM sees."""

    overall: GroupStats
    direct: GroupStats
    agent: GroupStats
    breakdowns: tuple[Breakdown, ...] = ()
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:  # Any: JSON-shaped payload for the prompt
        """Plain-dict form for JSON serialisation."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ResponseValidation:
    """Result of checking a hotel-analysis answer against the required JSON shape."""

    valid: bool
    data: dict[str, Any] | None = None  # Any: parsed model output
    error: str | None = None


@dataclass(frozen=True, slots=True)
class RunResult:
    """One persisted benchmark request. v1 fields keep their names."""

    backend: str
    model: str
    task_id: str
    category: str
    run: int
    cold: bool
    ttft_s: float | None
    total_s: float
    completion_tokens: int
    prompt_tokens: int | None
    tokens_per_s: float | None
    tokens_estimated: bool
    passed: bool | None
    output: str
    error: str | None
    analysis_type: str
    session_id: str
    timestamp: str
    temperature: float
    max_tokens: int
    runs: int
    prompt_version: str | None = None
    dataset: str | None = None
    dataset_hash: str | None = None
    dataset_rows: int | None = None
    resources: ResourceUsage = field(default_factory=ResourceUsage)
    response_valid: bool | None = None
    validation_error: str | None = None
    finish_reason: str | None = None

    def to_record(self) -> dict[str, Any]:  # Any: JSON record
        """Flat JSON-ready record including ``schema_version``."""
        record = asdict(self)
        resources = record.pop("resources")
        record["system_ram_before_mb"] = resources["ram_before_mb"]
        record["system_ram_after_mb"] = resources["ram_after_mb"]
        record["system_ram_peak_mb"] = resources["ram_peak_mb"]
        record["gpu_vram_before_mb"] = resources["vram_before_mb"]
        record["gpu_vram_after_mb"] = resources["vram_after_mb"]
        record["gpu_vram_peak_mb"] = resources["vram_peak_mb"]
        record["schema_version"] = SCHEMA_VERSION
        return record
