from __future__ import annotations

import pytest

from nfbench.infrastructure.resources import (
    ThreadedResourceMonitor,
    parse_nvidia_smi,
    system_ram_used_mb,
)


def test_parse_nvidia_smi_sums_gpus() -> None:
    assert parse_nvidia_smi("1129\n2000\n") == pytest.approx(3129.0)


@pytest.mark.parametrize("output", ["", "\n", "No devices were found", "N/A"])
def test_parse_nvidia_smi_unparsable_output_is_none(output: str) -> None:
    assert parse_nvidia_smi(output) is None


def test_system_ram_used_is_positive_number() -> None:
    value = system_ram_used_mb()
    assert value is not None
    assert value > 0


def test_monitor_without_gpu_reports_vram_unavailable_but_keeps_ram() -> None:
    monitor = ThreadedResourceMonitor(ram=lambda: 100.0, vram=lambda: None, interval_s=0.01)
    monitor.start()
    usage = monitor.stop()
    assert usage.ram_before_mb == usage.ram_after_mb == usage.ram_peak_mb == 100.0
    assert usage.vram_before_mb is None
    assert usage.vram_after_mb is None
    assert usage.vram_peak_mb is None


def test_monitor_peak_is_the_maximum_sample_seen() -> None:
    readings = iter([10.0, 50.0, 30.0, 20.0, 20.0, 20.0, 20.0])
    monitor = ThreadedResourceMonitor(
        ram=lambda: next(readings, 20.0), vram=lambda: 7.0, interval_s=100.0
    )
    monitor.start()  # 'before' = 10; background loop will not tick within the test
    usage = monitor.stop()  # 'after' = 50
    assert usage.ram_before_mb == 10.0
    assert usage.ram_after_mb == 50.0
    assert usage.ram_peak_mb == 50.0
    assert usage.vram_peak_mb == 7.0


def test_monitor_restart_discards_previous_samples() -> None:
    monitor = ThreadedResourceMonitor(ram=lambda: 5.0, vram=lambda: None, interval_s=100.0)
    monitor.start()
    monitor.stop()
    monitor.start()
    usage = monitor.stop()
    assert usage.ram_peak_mb == 5.0
