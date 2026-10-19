"""Describe the machine a run was made on: CPU, memory, GPU or none, operating system."""

from __future__ import annotations

import platform
import shutil
import subprocess
from collections.abc import Callable

import psutil

from nfbench.domain.service import BackendInfo, MachineInfo

_MB = 1024 * 1024
_NVIDIA_NAMES = ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"]


def parse_gpu_names(output: str) -> str | None:
    """The name of the first GPU in ``nvidia-smi`` output, or None when there is none."""
    for line in output.splitlines():
        if line.strip():
            return line.strip()
    return None


def read_gpu_name() -> str | None:
    """The first GPU name via ``nvidia-smi``; None without the tool or a GPU."""
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argument list
            _NVIDIA_NAMES, capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_gpu_names(completed.stdout) if completed.returncode == 0 else None


def read_cpu_name() -> str:
    """A readable CPU name from the platform."""
    return platform.processor() or platform.machine() or "unknown"


def read_cpu_cores() -> int:
    """Logical cores."""
    return psutil.cpu_count(logical=True) or 1


def read_memory_mb() -> int:
    """Total physical memory in MB."""
    return int(psutil.virtual_memory().total / _MB)


def read_os() -> str:
    """Operating system name and release."""
    return f"{platform.system()} {platform.release()}".strip()


class SystemMachineInspector:
    """Reads the machine from the operating system; every reader can be replaced in a test."""

    def __init__(
        self,
        backend_name: str,
        version_reader: Callable[[], str | None],
        gpu_reader: Callable[[], str | None] = read_gpu_name,
        cpu_reader: Callable[[], str] = read_cpu_name,
        cores_reader: Callable[[], int] = read_cpu_cores,
        memory_reader: Callable[[], int] = read_memory_mb,
        os_reader: Callable[[], str] = read_os,
    ) -> None:
        self._backend_name = backend_name
        self._version_reader = version_reader
        self._gpu_reader = gpu_reader
        self._cpu_reader = cpu_reader
        self._cores_reader = cores_reader
        self._memory_reader = memory_reader
        self._os_reader = os_reader

    def machine(self) -> MachineInfo:
        """The machine as it is now."""
        return MachineInfo(
            self._cpu_reader(),
            self._cores_reader(),
            self._memory_reader(),
            self._gpu_reader(),
            self._os_reader(),
        )

    def backend(self) -> BackendInfo:
        """The model server and its version (None when it cannot be read)."""
        return BackendInfo(self._backend_name, self._version_reader())
