from __future__ import annotations

import json

import pytest

from nfbench.application.delivery import DeliveryService
from nfbench.application.run_service import RunService
from nfbench.domain.errors import (
    InvalidRunRequestError,
    ModelInUseError,
    ModelNotInstalledError,
    QueueFullError,
    ResultNotReadyError,
    RunNotFoundError,
)
from nfbench.domain.service import (
    MAX_LISTED_RUNS,
    DeliveryOutcome,
    DeliveryState,
    RunState,
    StartRunRequest,
)
from tests.service_fakes import (
    HOTEL,
    FakeCatalog,
    FakeEpoch,
    FakeExecutor,
    FakeInspector,
    FakeSender,
    MemoryPendingStore,
)

NOW = 1_792_404_000.0


class _Parts:
    def __init__(self, sender: FakeSender | None = None, fail_with: str | None = None) -> None:
        self.catalog = FakeCatalog("m1", "m2", "m3")
        self.executor = FakeExecutor(fail_with)
        self.sender = sender or FakeSender()
        self.store = MemoryPendingStore()
        self.clock = FakeEpoch(NOW)
        delivery = DeliveryService(self.sender, self.store, self.clock)
        self.service = RunService(
            self.catalog,
            self.executor,
            lambda: HOTEL,
            FakeInspector(),
            delivery,
            clock=self.clock,
        )


def _request(*models: str) -> StartRunRequest:
    return StartRunRequest(models=models or ("m1",))


def test_start_installed_models_returns_a_queued_run() -> None:
    parts = _Parts()

    status = parts.service.start(_request("m1", "m2"))

    assert status.state is RunState.QUEUED
    assert status.delivery is DeliveryState.NOT_READY
    assert status.models == ("m1", "m2")
    assert parts.service.status(status.run_id) == status


@pytest.mark.parametrize(
    "request_",
    [
        StartRunRequest(models=()),
        StartRunRequest(models=("m1", "m1")),
        StartRunRequest(models=("m1", "m2", "m3", "m4", "m5")),
        StartRunRequest(models=("m1",), runs=0),
        StartRunRequest(models=("m1",), runs=6),
        StartRunRequest(models=("m1",), hotel_analysis=False, deterministic_tasks=False),
    ],
)
def test_start_invalid_request_is_refused(request_: StartRunRequest) -> None:
    with pytest.raises(InvalidRunRequestError):
        _Parts().service.start(request_)


def test_start_model_that_is_not_installed_is_refused() -> None:
    with pytest.raises(ModelNotInstalledError, match="unknown"):
        _Parts().service.start(_request("unknown"))


def test_start_third_waiting_run_is_refused_when_the_queue_is_full() -> None:
    parts = _Parts()
    parts.service.start(_request())
    parts.service.start(_request())

    with pytest.raises(QueueFullError):
        parts.service.start(_request())


def test_start_after_a_queued_run_was_taken_there_is_room_again() -> None:
    parts = _Parts()
    parts.service.start(_request())
    parts.service.start(_request())
    parts.service.tick()

    status = parts.service.start(_request())

    assert status.state is RunState.QUEUED


def test_status_unknown_run_raises_not_found() -> None:
    with pytest.raises(RunNotFoundError):
        _Parts().service.status("nope")


def test_tick_runs_the_oldest_queued_run_with_the_requested_options() -> None:
    parts = _Parts()
    first = parts.service.start(StartRunRequest(("m2", "m1"), True, True, 2))
    second = parts.service.start(_request("m3"))

    worked = parts.service.tick()

    assert worked is True
    (models, config), *rest = parts.executor.calls
    assert not rest
    assert models == ["m2", "m1"]
    assert (config.runs, config.hotel_analysis, config.deterministic_tasks) == (2, True, True)
    assert parts.service.status(first.run_id).state is RunState.DONE
    assert parts.service.status(second.run_id).state is RunState.QUEUED


def test_tick_finished_run_is_saved_sent_and_reported_delivered() -> None:
    parts = _Parts(FakeSender(DeliveryOutcome.DELIVERED))
    run = parts.service.start(_request("m1"))

    parts.service.tick()
    after_run = parts.service.status(run.run_id)
    parts.service.tick()
    after_delivery = parts.service.status(run.run_id)

    assert after_run.delivery is DeliveryState.PENDING
    assert after_delivery.delivery is DeliveryState.DELIVERED
    assert parts.store.items[run.run_id]["run_id"] == run.run_id
    assert parts.sender.sent[0]["run_id"] == run.run_id


def test_tick_web_api_down_keeps_the_result_pending_with_the_run_done() -> None:
    parts = _Parts(FakeSender(DeliveryOutcome.RETRY))
    run = parts.service.start(_request("m1"))

    parts.service.tick()
    parts.service.tick()
    status = parts.service.status(run.run_id)

    assert status.state is RunState.DONE
    assert status.delivery is DeliveryState.PENDING
    assert run.run_id in parts.store.items


def test_tick_web_api_gone_for_fifteen_minutes_reports_delivery_failed() -> None:
    parts = _Parts(FakeSender(DeliveryOutcome.RETRY))
    run = parts.service.start(_request("m1"))
    parts.service.tick()
    parts.service.tick()

    parts.clock.now = NOW + 16 * 60
    parts.service.tick()

    assert parts.service.status(run.run_id).delivery is DeliveryState.FAILED
    assert parts.store.failed == [run.run_id]


def test_tick_executor_failure_marks_the_run_failed_with_the_reason() -> None:
    parts = _Parts(fail_with="ollama exploded")
    run = parts.service.start(_request("m1"))

    parts.service.tick()
    status = parts.service.status(run.run_id)

    assert status.state is RunState.FAILED
    assert status.error == "ollama exploded"
    assert status.delivery is DeliveryState.NOT_READY
    assert not parts.store.items


def test_tick_nothing_to_do_returns_false() -> None:
    assert _Parts().service.tick() is False


def test_restore_pending_results_after_a_restart_are_delivered() -> None:
    parts = _Parts(FakeSender(DeliveryOutcome.DELIVERED))
    parts.store.save("old", {"run_id": "old", "finished_at": "2026-10-19T10:00:00+00:00"})

    parts.service.restore()
    parts.service.tick()

    assert parts.store.delivered == ["old"]


def test_installed_models_lists_the_catalog() -> None:
    assert _Parts().service.installed_models() == ("m1", "m2", "m3")


def test_delete_if_unused_a_queued_run_that_names_the_model_blocks_the_delete() -> None:
    parts = _Parts()
    parts.service.start(StartRunRequest(("m1",)))
    called: list[str] = []

    def delete() -> bool:
        called.append("deleted")
        return True

    with pytest.raises(ModelInUseError):
        parts.service.delete_if_unused("m1", delete)

    assert called == []


def test_delete_if_unused_a_model_that_no_run_names_is_deleted() -> None:
    parts = _Parts()
    parts.service.start(StartRunRequest(("m1",)))

    assert parts.service.delete_if_unused("m2", lambda: True) is True


def test_delete_if_unused_a_finished_run_does_not_block_the_delete() -> None:
    parts = _Parts()
    parts.service.start(StartRunRequest(("m1",)))
    parts.service.tick()

    assert parts.service.delete_if_unused("m1", lambda: True) is True


def test_delete_if_unused_passes_on_the_answer_of_the_delete() -> None:
    assert _Parts().service.delete_if_unused("m1", lambda: False) is False


def test_start_a_model_that_was_deleted_after_the_check_of_an_earlier_run_is_refused() -> None:
    parts = _Parts()
    parts.service.delete_if_unused("m1", lambda: _remove(parts, "m1"))

    with pytest.raises(ModelNotInstalledError):
        parts.service.start(StartRunRequest(("m1",)))


def _remove(parts: _Parts, model: str) -> bool:
    parts.catalog.models = tuple(m for m in parts.catalog.models if m != model)
    return True


def test_list_runs_no_run_is_an_empty_tuple() -> None:
    assert _Parts().service.list_runs() == ()


def test_list_runs_returns_the_runs_newest_first_with_their_state() -> None:
    parts = _Parts()
    first = parts.service.start(StartRunRequest(("m1",)))
    second = parts.service.start(StartRunRequest(("m2",)))

    listed = parts.service.list_runs()

    assert [run.run_id for run in listed] == [second.run_id, first.run_id]
    assert [run.state for run in listed] == [RunState.QUEUED, RunState.QUEUED]


def test_list_runs_shows_a_change_of_state_in_the_next_call() -> None:
    parts = _Parts()
    run = parts.service.start(StartRunRequest(("m1",)))
    before = parts.service.list_runs()[0].state

    parts.service.tick()

    after = parts.service.list_runs()[0]
    assert (before, after.run_id, after.state) == (RunState.QUEUED, run.run_id, RunState.DONE)


def test_list_runs_keeps_the_newest_twenty() -> None:
    parts = _Parts()
    ids = []
    for _ in range(MAX_LISTED_RUNS + 3):
        ids.append(parts.service.start(StartRunRequest(("m1",))).run_id)
        parts.service.tick()

    listed = parts.service.list_runs()

    assert len(listed) == MAX_LISTED_RUNS
    assert [run.run_id for run in listed] == list(reversed(ids))[:MAX_LISTED_RUNS]


def _answer(summary: str) -> str:
    return json.dumps(
        {
            "summary": summary,
            "overall_cancellation": {"rate": 0.37, "interpretation": "i"},
            "direct_customers": {"rate": 0.3, "interpretation": "i"},
            "agent_bookings": {"rate": 0.4, "interpretation": "i"},
            "key_findings": ["a"],
            "limitations": ["b"],
        }
    )


def test_summaries_of_a_finished_run_come_from_the_stored_result() -> None:
    parts = _Parts()
    parts.executor.answers = {
        "m1": (_answer("m1 says so."), "stop"),
        "m2": ('{"summary": "Canc', "length"),
    }
    run_id = parts.service.start(_request("m1", "m2")).run_id
    parts.service.tick()

    comparison = parts.service.summaries(run_id)

    assert comparison.run == 0
    assert [(e.model, e.summary) for e in comparison.entries] == [
        ("m1", "m1 says so."),
        ("m2", None),
    ]
    assert comparison.entries[1].problem == "cut off at the maximum output tokens"


def test_summaries_of_an_unknown_run_raise_run_not_found() -> None:
    with pytest.raises(RunNotFoundError):
        _Parts().service.summaries("ghost")


def test_summaries_of_a_run_that_has_no_result_yet_raise_result_not_ready() -> None:
    parts = _Parts()
    run_id = parts.service.start(_request("m1")).run_id

    with pytest.raises(ResultNotReadyError):
        parts.service.summaries(run_id)


def test_summaries_of_a_run_that_failed_raise_result_not_ready() -> None:
    parts = _Parts(fail_with="boom")
    run_id = parts.service.start(_request("m1")).run_id
    parts.service.tick()

    with pytest.raises(ResultNotReadyError):
        parts.service.summaries(run_id)
