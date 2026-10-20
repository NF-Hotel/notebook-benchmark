from __future__ import annotations

import json

from nfbench.application.benchmark import BenchmarkController, HotelInput, ModelSelection
from nfbench.application.prompts import HOTEL_PROMPT_VERSION, build_hotel_prompt
from nfbench.domain.models import (
    BenchmarkConfig,
    DatasetInfo,
    GroupStats,
    HotelSummary,
    StreamChunk,
)
from tests.fakes import FakeBackend, FakeMonitor, MemoryStore

ANSWER = json.dumps(
    {
        "summary": "s",
        "overall_cancellation": {"rate": 0.5, "interpretation": "i"},
        "direct_customers": {"rate": 0.4, "interpretation": "i"},
        "agent_bookings": {"rate": 0.6, "interpretation": "i"},
        "key_findings": ["x"],
        "limitations": ["y"],
    }
)
SUMMARY = HotelSummary(GroupStats(10, 5, 0.5), GroupStats(5, 2, 0.4), GroupStats(5, 3, 0.6))
INFO = DatasetInfo("d.csv", "/x/d.csv", "abc123", 10, ("a",), {"a": "Int64"}, {"a": 0})
HOTEL = HotelInput(INFO, SUMMARY)


def _controller(backend: FakeBackend, store: MemoryStore) -> BenchmarkController:
    return BenchmarkController({backend.name: backend}, FakeMonitor(), store)


def test_run_records_metadata_validation_and_resources() -> None:
    backend = FakeBackend(
        "ollama", [StreamChunk(text=ANSWER), StreamChunk(completion_tokens=12, prompt_tokens=99)]
    )
    store = MemoryStore()
    config = BenchmarkConfig(temperature=0.2, max_tokens=256, runs=1)
    results = _controller(backend, store).run([ModelSelection("ollama", "m1")], config, HOTEL)
    assert store.results == results
    (result,) = results
    assert result.response_valid is True
    assert result.dataset_hash == "abc123"
    assert result.dataset_rows == 10
    assert result.prompt_version == HOTEL_PROMPT_VERSION
    assert (result.temperature, result.max_tokens) == (0.2, 256)
    assert result.completion_tokens == 12
    assert result.resources.ram_peak_mb == 3.0
    assert result.passed is None  # hotel analysis has no pass/fail
    record = result.to_record()
    assert record["schema_version"] == 2
    assert record["system_ram_peak_mb"] == 3.0
    assert record["gpu_vram_peak_mb"] is None


def test_run_sends_identical_prompt_and_settings_to_every_model() -> None:
    backend = FakeBackend("ollama", [StreamChunk(text=ANSWER)])
    controller = _controller(backend, MemoryStore())
    selections = [ModelSelection("ollama", "a"), ModelSelection("ollama", "b")]
    controller.run(selections, BenchmarkConfig(), HOTEL)
    first, second = backend.requests
    assert first.prompt == second.prompt == build_hotel_prompt(SUMMARY)
    assert (first.temperature, first.max_tokens) == (second.temperature, second.max_tokens)
    assert (first.model, second.model) == ("a", "b")


def test_first_request_per_model_is_cold_and_later_ones_warm() -> None:
    backend = FakeBackend("ollama", [StreamChunk(text=ANSWER)])
    results = _controller(backend, MemoryStore()).run(
        [ModelSelection("ollama", "a"), ModelSelection("ollama", "b")],
        BenchmarkConfig(runs=2),
        HOTEL,
    )
    assert [(r.model, r.run, r.cold) for r in results] == [
        ("a", 0, True),
        ("a", 1, False),
        ("b", 0, True),
        ("b", 1, False),
    ]


def test_backend_failure_is_recorded_and_benchmark_continues() -> None:
    bad = FakeBackend("ollama", fail_with="boom")
    good = FakeBackend("lmstudio", [StreamChunk(text=ANSWER)])
    controller = BenchmarkController(
        {"ollama": bad, "lmstudio": good}, FakeMonitor(), MemoryStore()
    )
    results = controller.run(
        [ModelSelection("ollama", "a"), ModelSelection("lmstudio", "b")], BenchmarkConfig(), HOTEL
    )
    assert results[0].error == "boom"
    assert results[0].response_valid is None
    assert results[1].error is None
    assert results[1].response_valid is True


def test_unknown_backend_is_an_error_result_not_a_crash() -> None:
    results = _controller(FakeBackend("ollama"), MemoryStore()).run(
        [ModelSelection("nope", "a")], BenchmarkConfig(), HOTEL
    )
    assert results[0].error is not None
    assert "nope" in results[0].error


def test_invalid_answer_keeps_raw_response_and_reason() -> None:
    backend = FakeBackend("ollama", [StreamChunk(text="not json")])
    (result,) = _controller(backend, MemoryStore()).run(
        [ModelSelection("ollama", "a")], BenchmarkConfig(), HOTEL
    )
    assert result.output == "not json"
    assert result.response_valid is False
    assert result.validation_error == "no valid JSON object found"


def test_deterministic_tasks_keep_pass_fail() -> None:
    backend = FakeBackend("ollama", [StreamChunk(text="155")])
    config = BenchmarkConfig(hotel_analysis=False, deterministic_tasks=True)
    results = _controller(backend, MemoryStore()).run([ModelSelection("ollama", "a")], config)
    by_id = {r.task_id: r for r in results}
    assert by_id["math-1"].passed is True
    assert by_id["logic-1"].passed is False
    assert by_id["summ-1"].passed is None
    assert all(r.analysis_type == "deterministic_task" for r in results)


def test_progress_callback_reports_every_job() -> None:
    backend = FakeBackend("ollama", [StreamChunk(text=ANSWER)])
    seen: list[tuple[int, int]] = []
    _controller(backend, MemoryStore()).run(
        [ModelSelection("ollama", "a")],
        BenchmarkConfig(runs=2),
        HOTEL,
        lambda done, total, _label: seen.append((done, total)),
    )
    assert seen == [(0, 2), (1, 2), (2, 2)]


def test_truncated_invalid_answer_is_explained_by_finish_reason() -> None:
    backend = FakeBackend(
        "ollama", [StreamChunk(text='{"summary": "cut'), StreamChunk(finish_reason="length")]
    )
    (result,) = _controller(backend, MemoryStore()).run(
        [ModelSelection("ollama", "a")], BenchmarkConfig(), HOTEL
    )
    assert result.response_valid is False
    assert result.finish_reason == "length"
    assert result.validation_error == "no valid JSON object found (output cut off at max_tokens)"


def test_default_max_tokens_leaves_room_for_the_json_answer() -> None:
    assert BenchmarkConfig().max_tokens == 32768
