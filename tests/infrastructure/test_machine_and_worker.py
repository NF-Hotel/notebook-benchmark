from __future__ import annotations

import threading

from nfbench.infrastructure.machine import SystemMachineInspector, parse_gpu_names
from nfbench.infrastructure.worker import BackgroundWorker


def test_parse_gpu_names_takes_the_first_gpu_of_nvidia_smi_output() -> None:
    assert parse_gpu_names("NVIDIA RTX 4090\nNVIDIA RTX 4090\n") == "NVIDIA RTX 4090"


def test_parse_gpu_names_empty_or_blank_output_is_no_gpu() -> None:
    assert parse_gpu_names("") is None
    assert parse_gpu_names("  \n") is None


def test_machine_describes_cpu_memory_gpu_and_os_from_the_readers() -> None:
    inspector = SystemMachineInspector(
        "ollama",
        version_reader=lambda: "0.5.1",
        gpu_reader=lambda: None,
        cpu_reader=lambda: "Test CPU",
        cores_reader=lambda: 8,
        memory_reader=lambda: 16384,
        os_reader=lambda: "Linux 6.8",
    )

    machine = inspector.machine()

    assert (machine.cpu, machine.cpu_cores, machine.memory_mb) == ("Test CPU", 8, 16384)
    assert machine.gpu is None
    assert machine.os == "Linux 6.8"


def test_backend_names_the_server_and_its_version() -> None:
    inspector = SystemMachineInspector("ollama", version_reader=lambda: "0.5.1")

    backend = inspector.backend()

    assert (backend.name, backend.version) == ("ollama", "0.5.1")


def test_backend_unknown_version_is_none() -> None:
    assert SystemMachineInspector("ollama", version_reader=lambda: None).backend().version is None


def test_machine_real_readers_give_plausible_values() -> None:
    machine = SystemMachineInspector("ollama", version_reader=lambda: None).machine()

    assert machine.cpu_cores >= 1
    assert machine.memory_mb > 0
    assert machine.cpu
    assert machine.os


def test_worker_calls_tick_until_stopped() -> None:
    calls: list[int] = []
    done = threading.Event()

    def tick() -> bool:
        calls.append(1)
        if len(calls) >= 3:
            done.set()
        return len(calls) < 3

    worker = BackgroundWorker(tick, idle_s=0.01)
    worker.start()
    assert done.wait(timeout=5)
    worker.stop()

    assert len(calls) >= 3


def test_worker_survives_a_tick_that_raises() -> None:
    calls: list[int] = []
    done = threading.Event()

    def tick() -> bool:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("boom")
        done.set()
        return False

    worker = BackgroundWorker(tick, idle_s=0.01)
    worker.start()
    assert done.wait(timeout=5)
    worker.stop()

    assert len(calls) >= 2
