from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from nfbench.adapters.result_store import RESULT_COLUMNS, JsonlResultStore
from nfbench.domain.models import ResourceUsage, RunResult


def _result(model: str = "m") -> RunResult:
    return RunResult(
        backend="ollama", model=model, task_id="hotel-cancellation", category="analysis", run=0,
        cold=True, ttft_s=0.5, total_s=2.0, completion_tokens=10, prompt_tokens=None,
        tokens_per_s=5.0, tokens_estimated=False, passed=None, output="{}", error=None,
        analysis_type="hotel_cancellation", session_id="s1", timestamp="2026-09-27T10:00:00+00:00",
        temperature=0.0, max_tokens=1024, runs=1, dataset="d.csv", dataset_hash="h", dataset_rows=3,
        resources=ResourceUsage(1.0, 2.0, 3.0, None, None, None),
    )  # fmt: skip


def test_append_and_load_round_trip_keeps_metadata(tmp_path: Path) -> None:
    store = JsonlResultStore(tmp_path / "out" / "results.jsonl")
    store.append(_result("a"))
    store.append(_result("b"))
    records = store.load_records()
    assert [r["model"] for r in records] == ["a", "b"]
    first = records[0]
    assert first["schema_version"] == 2
    assert first["dataset_hash"] == "h"
    assert first["system_ram_peak_mb"] == 3.0
    assert first["gpu_vram_peak_mb"] is None
    assert first["cold"] is True


def test_load_frame_is_empty_without_file(tmp_path: Path) -> None:
    assert JsonlResultStore(tmp_path / "none.jsonl").load_frame().is_empty()


def test_load_reads_legacy_v1_rows_and_skips_corrupt_lines(tmp_path: Path) -> None:
    path = tmp_path / "results.jsonl"
    legacy = {
        "backend": "ollama",
        "model": "phi4",
        "task_id": "math-1",
        "ttft_s": 1.0,
        "passed": True,
    }
    path.write_text(json.dumps(legacy) + "\n{broken\n\n", encoding="utf-8")
    store = JsonlResultStore(path)
    store.append(_result())
    frame = store.load_frame()
    assert frame.height == 2
    assert frame["schema_version"].to_list() == [1, 2]
    assert frame["analysis_type"].to_list() == ["deterministic_task", "hotel_cancellation"]


def test_load_frame_adds_missing_v2_columns_for_legacy_only_files(tmp_path: Path) -> None:
    path = tmp_path / "results.jsonl"
    path.write_text(json.dumps({"backend": "ollama", "model": "phi4"}) + "\n", encoding="utf-8")
    frame = JsonlResultStore(path).load_frame()
    assert set(RESULT_COLUMNS) <= set(frame.columns)
    assert frame["cold"].to_list() == [None]
    assert frame["cold"].dtype == pl.Boolean  # all-null columns still get usable dtypes
    assert frame["ttft_s"].dtype == pl.Float64
