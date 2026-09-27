"""RAM and GPU VRAM sampling. Unavailable sources report None instead of failing."""

from __future__ import annotations

import logging
import shutil
import subprocess
import threading
from collections.abc import Callable

import psutil

from nfbench.domain.models import ResourceUsage

logger = logging.getLogger(__name__)

_MB = 1024 * 1024
_NVIDIA_QUERY = ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"]

Sampler = Callable[[], float | None]


def system_ram_used_mb() -> float | None:
    """System-wide used physical memory in MB (the model server is a separate process)."""
    try:
        return float(psutil.virtual_memory().used) / _MB
    except (OSError, psutil.Error):
        logger.warning("system RAM could not be read", exc_info=True)
        return None


def parse_nvidia_smi(output: str) -> float | None:
    """Sum of per-GPU ``memory.used`` (MiB) from nvidia-smi CSV output; None if unparsable."""
    values: list[float] = []
    for line in output.splitlines():
        if line.strip():
            try:
                values.append(float(line.strip()))
            except ValueError:
                return None
    return sum(values) if values else None


def nvidia_vram_used_mb() -> float | None:
    """Total GPU memory in use via ``nvidia-smi``; None when the tool or a GPU is missing."""
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argument list
            _NVIDIA_QUERY, capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_nvidia_smi(completed.stdout) if completed.returncode == 0 else None


def _peak(values: list[float | None]) -> float | None:
    known = [v for v in values if v is not None]
    return max(known) if known else None


class ThreadedResourceMonitor:
    """Samples RAM and VRAM in a background thread between ``start`` and ``stop``."""

    def __init__(
        self,
        ram: Sampler = system_ram_used_mb,
        vram: Sampler = nvidia_vram_used_mb,
        interval_s: float = 0.25,
    ) -> None:
        self._ram = ram
        self._vram = vram
        self._interval = interval_s
        self._ram_samples: list[float | None] = []
        self._vram_samples: list[float | None] = []
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._vram_available = True

    def _sample(self) -> None:
        self._ram_samples.append(self._ram())
        vram = self._vram() if self._vram_available else None
        if vram is None:
            self._vram_available = False  # do not keep spawning a missing tool
        self._vram_samples.append(vram)

    def _loop(self) -> None:
        while not self._stop_event.wait(self._interval):
            self._sample()

    def start(self) -> None:
        """Take the 'before' sample and start sampling."""
        self._ram_samples, self._vram_samples = [], []
        self._vram_available = True
        self._stop_event.clear()
        self._sample()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> ResourceUsage:
        """Take the 'after' sample, stop the thread and return before / after / peak."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None
        self._sample()
        return ResourceUsage(
            ram_before_mb=self._ram_samples[0],
            ram_after_mb=self._ram_samples[-1],
            ram_peak_mb=_peak(self._ram_samples),
            vram_before_mb=self._vram_samples[0],
            vram_after_mb=self._vram_samples[-1],
            vram_peak_mb=_peak(self._vram_samples),
        )
