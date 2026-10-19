"""A background thread that calls the service's ``tick`` so that the API never waits for a run."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)


class BackgroundWorker:
    """Calls ``tick`` again at once while it reports work, else after ``idle_s`` seconds."""

    def __init__(self, tick: Callable[[], bool], idle_s: float = 1.0) -> None:
        self._tick = tick
        self._idle_s = idle_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="benchmark-worker", daemon=True)

    def start(self) -> None:
        """Start the thread."""
        self._thread.start()

    def stop(self) -> None:
        """Ask the thread to end and wait for it."""
        self._stop.set()
        self._thread.join(timeout=10)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                worked = self._tick()
            except Exception:
                logger.exception("the worker tick failed; trying again")
                worked = False
            if not worked:
                self._stop.wait(self._idle_s)
