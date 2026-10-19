from __future__ import annotations

import pytest

from nfbench.application.delivery import DeliveryService
from nfbench.application.run_service import RunService
from nfbench.domain.errors import (
    InvalidRunRequestError,
    ModelNotInstalledError,
    QueueFullError,
    RunNotFoundError,
)
from nfbench.domain.service import DeliveryOutcome, DeliveryState, RunState, StartRunRequest
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
        self.executor = FakeExecutor(fail_with)
        self.sender = sender or FakeSender()
        self.store = MemoryPendingStore()
        self.clock = FakeEpoch(NOW)
        delivery = DeliveryService(self.sender, self.store, self.clock)
        self.service = RunService(
            FakeCatalog("m1", "m2", "m3"),
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
