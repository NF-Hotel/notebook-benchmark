from __future__ import annotations

from nfbench.application.delivery import DeliveryService
from nfbench.domain.service import DeliveryOutcome, DeliveryState
from tests.service_fakes import FakeEpoch, FakeSender, MemoryPendingStore

FINISHED = "2026-10-19T10:00:00+00:00"
FINISHED_EPOCH = 1_792_404_000.0  # 2026-10-19T10:00:00Z
PAYLOAD = {"run_id": "r1", "finished_at": FINISHED}


def _service(
    sender: FakeSender, now: float = FINISHED_EPOCH
) -> tuple[DeliveryService, MemoryPendingStore, FakeEpoch]:
    store = MemoryPendingStore()
    clock = FakeEpoch(now)
    return DeliveryService(sender, store, clock), store, clock


def test_submit_saves_the_result_before_any_attempt() -> None:
    service, store, _ = _service(FakeSender())

    service.submit(PAYLOAD)

    assert store.items == {"r1": PAYLOAD}


def test_deliver_due_delivered_marks_the_store_and_reports_it() -> None:
    sender = FakeSender(DeliveryOutcome.DELIVERED)
    service, store, _ = _service(sender)
    service.submit(PAYLOAD)

    changes = service.deliver_due()

    assert changes == {"r1": DeliveryState.DELIVERED}
    assert store.delivered == ["r1"]
    assert len(sender.sent) == 1


def test_deliver_due_after_delivery_does_not_send_again() -> None:
    sender = FakeSender(DeliveryOutcome.DELIVERED)
    service, _, _ = _service(sender)
    service.submit(PAYLOAD)
    service.deliver_due()

    assert service.deliver_due() == {}
    assert len(sender.sent) == 1


def test_deliver_due_retry_waits_five_seconds_then_doubles() -> None:
    sender = FakeSender(DeliveryOutcome.RETRY)
    service, _, clock = _service(sender)
    service.submit(PAYLOAD)

    service.deliver_due()  # attempt 1 at t0
    clock.now = FINISHED_EPOCH + 4
    service.deliver_due()  # not yet due
    clock.now = FINISHED_EPOCH + 5
    service.deliver_due()  # attempt 2, next delay 10
    clock.now = FINISHED_EPOCH + 14
    service.deliver_due()  # not yet due
    clock.now = FINISHED_EPOCH + 15
    service.deliver_due()  # attempt 3

    assert len(sender.sent) == 3


def test_deliver_due_retry_then_delivered_marks_the_store() -> None:
    sender = FakeSender(DeliveryOutcome.RETRY, DeliveryOutcome.DELIVERED)
    service, store, clock = _service(sender)
    service.submit(PAYLOAD)
    service.deliver_due()

    clock.now = FINISHED_EPOCH + 5
    changes = service.deliver_due()

    assert changes == {"r1": DeliveryState.DELIVERED}
    assert store.delivered == ["r1"]


def test_deliver_due_after_fifteen_minutes_gives_up_and_keeps_the_file() -> None:
    sender = FakeSender(DeliveryOutcome.RETRY)
    service, store, clock = _service(sender)
    service.submit(PAYLOAD)
    service.deliver_due()

    clock.now = FINISHED_EPOCH + 15 * 60
    changes = service.deliver_due()

    assert changes == {"r1": DeliveryState.FAILED}
    assert store.failed == ["r1"]
    assert "r1" in store.items


def test_deliver_due_rejected_is_not_retried() -> None:
    sender = FakeSender(DeliveryOutcome.REJECTED)
    service, store, clock = _service(sender)
    service.submit(PAYLOAD)

    changes = service.deliver_due()
    clock.now = FINISHED_EPOCH + 60
    again = service.deliver_due()

    assert changes == {"r1": DeliveryState.FAILED}
    assert again == {}
    assert store.failed == ["r1"]
    assert len(sender.sent) == 1


def test_restore_resumes_results_that_were_pending_before_a_restart() -> None:
    sender = FakeSender(DeliveryOutcome.DELIVERED)
    service, store, _ = _service(sender)
    store.save("r9", {"run_id": "r9", "finished_at": FINISHED})

    restored = service.restore()
    changes = service.deliver_due()

    assert restored == ["r9"]
    assert changes == {"r9": DeliveryState.DELIVERED}


def test_restore_late_result_is_tried_once_more_then_given_up() -> None:
    sender = FakeSender(DeliveryOutcome.RETRY)
    service, store, _ = _service(sender, now=FINISHED_EPOCH + 3 * 3600)
    store.save("r9", {"run_id": "r9", "finished_at": FINISHED})

    service.restore()
    changes = service.deliver_due()

    assert changes == {"r9": DeliveryState.FAILED}
    assert len(sender.sent) == 1
