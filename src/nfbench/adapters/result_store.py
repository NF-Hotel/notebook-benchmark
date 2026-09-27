"""Append-only JSONL result store; reads schema v1 (deterministic tasks only) and v2 rows."""

from __future__ import annotations

import json
import logging
from dataclasses import fields
from pathlib import Path

import polars as pl

from nfbench.domain.models import ANALYSIS_TASK, RunResult

logger = logging.getLogger(__name__)

_RESOURCE_COLUMNS = (
    "system_ram_before_mb",
    "system_ram_after_mb",
    "system_ram_peak_mb",
    "gpu_vram_before_mb",
    "gpu_vram_after_mb",
    "gpu_vram_peak_mb",
)
RESULT_COLUMNS: tuple[str, ...] = (
    *(f.name for f in fields(RunResult) if f.name != "resources"),
    *_RESOURCE_COLUMNS,
    "schema_version",
)

_BOOLEAN_COLUMNS = frozenset({"cold", "passed", "response_valid", "tokens_estimated"})
_NUMERIC_COLUMNS = frozenset(
    {
        "run", "runs", "ttft_s", "total_s", "completion_tokens", "prompt_tokens", "tokens_per_s",
        "temperature", "max_tokens", "dataset_rows", "schema_version", *_RESOURCE_COLUMNS,
    }
)  # fmt: skip

DEFAULT_RESULTS_PATH = Path(__file__).resolve().parents[3] / "output" / "results.jsonl"


class JsonlResultStore:
    """One JSON object per line, written immediately so a crash loses nothing."""

    def __init__(self, path: Path = DEFAULT_RESULTS_PATH) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        """Location of the results file."""
        return self._path

    def append(self, result: RunResult) -> None:
        """Persist one result."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result.to_record()) + "\n")

    def load_records(self) -> list[dict[str, object]]:
        """All stored rows; unreadable lines are skipped with a warning.

        v1 rows (no ``schema_version``) are upgraded in memory: they are deterministic-task
        runs without cold/warm information.
        """
        if not self._path.exists():
            return []
        records: list[dict[str, object]] = []
        with self._path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("skipping unreadable line %d in %s", number, self._path)
                    continue
                if isinstance(row, dict):
                    records.append(_upgrade(row))
        return records

    def load_frame(self) -> pl.DataFrame:
        """All rows as a dataframe with every v2 column present (null where v1 lacks it).

        Empty frame when there are no rows.
        """
        records = self.load_records()
        if not records:
            return pl.DataFrame()
        frame = pl.DataFrame(records, infer_schema_length=None)
        missing = [c for c in RESULT_COLUMNS if c not in frame.columns]
        frame = frame.with_columns(*(pl.lit(None).alias(c) for c in missing))
        return frame.with_columns(
            pl.col(name).cast(_dtype_for(name))
            for name, dtype in frame.schema.items()
            if dtype == pl.Null
        )


def _dtype_for(column: str) -> pl.DataType | type[pl.DataType]:
    """Concrete dtype for a column that is entirely null (so charts and filters type-check)."""
    if column in _BOOLEAN_COLUMNS:
        return pl.Boolean
    return pl.Float64 if column in _NUMERIC_COLUMNS else pl.String


def _upgrade(row: dict[str, object]) -> dict[str, object]:
    if "schema_version" in row:
        return row
    upgraded = dict(row)
    upgraded.setdefault("analysis_type", ANALYSIS_TASK)
    upgraded.setdefault("session_id", "legacy-v1")
    upgraded["schema_version"] = 1
    return upgraded
