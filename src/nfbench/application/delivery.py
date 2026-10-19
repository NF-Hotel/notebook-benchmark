"""Deliver finished results to the web API: save first, retry with a growing delay, give up late."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from nfbench.application.ports import Payload, PendingResultStore, ResultSender
from nfbench.domain.service import (
    DELIVERY_WINDOW_S,
    FIRST_RETRY_DELAY_S,
    DeliveryOutcome,
    DeliveryState,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _Pending:
    payload: Payload
    deadline: float
    next_at: float
    delay: float


class DeliveryService:
    """Sends each result until the web API has it (ADR-0001).

    A result is written to the store before the first attempt. A failed attempt is repeated after
    5 seconds, then 10, 20 and so on, until 15 minutes after the run ended. A rejection (400, 401)
    is a defect and is not repeated. The file stays in the store when delivery fails.
    """

    def __init__(
        self,
        sender: ResultSender,
        store: PendingResultStore,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._sender = sender
        self._store = store
        self._clock = clock
        self._pending: dict[str, _Pending] = {}

    def submit(self, payload: Payload) -> None:
        """Keep a finished result and schedule its first attempt for now."""
        run_id = str(payload["run_id"])
        self._store.save(run_id, payload)
        self._schedule(run_id, payload)

    def restore(self) -> list[str]:
        """Pick up the results that were not delivered before a restart."""
        restored = []
        for run_id, payload in self._store.pending():
            if run_id not in self._pending:
                self._schedule(run_id, payload)
                restored.append(run_id)
        return restored

    def deliver_due(self) -> dict[str, DeliveryState]:
        """Make the attempts that are due; return the runs whose delivery has ended."""
        now = self._clock()
        ended: dict[str, DeliveryState] = {}
        for run_id, item in list(self._pending.items()):
            if item.next_at > now:
                continue
            state = self._attempt(run_id, item, now)
            if state is not None:
                ended[run_id] = state
                del self._pending[run_id]
        return ended

    def _schedule(self, run_id: str, payload: Payload) -> None:
        now = self._clock()
        finished = datetime.fromisoformat(str(payload["finished_at"])).timestamp()
        self._pending[run_id] = _Pending(
            payload, finished + DELIVERY_WINDOW_S, now, FIRST_RETRY_DELAY_S
        )

    def _attempt(self, run_id: str, item: _Pending, now: float) -> DeliveryState | None:
        outcome = self._sender.send(item.payload)
        if outcome is DeliveryOutcome.DELIVERED:
            self._store.mark_delivered(run_id)
            return DeliveryState.DELIVERED
        if outcome is DeliveryOutcome.REJECTED:
            logger.error("the web API rejected run %s; not retried", run_id)
            self._store.mark_failed(run_id)
            return DeliveryState.FAILED
        if now >= item.deadline:
            logger.error("run %s was not delivered within the retry window", run_id)
            self._store.mark_failed(run_id)
            return DeliveryState.FAILED
        item.next_at = min(now + item.delay, item.deadline)
        item.delay *= 2
        return None
