from __future__ import annotations

from pathlib import Path
from typing import Any

import jsonschema
import yaml

from nfbench.application.payload import build_result_payload
from tests.service_fakes import BACKEND, HOTEL, MACHINE, make_result

CONTRACT = Path(__file__).resolve().parents[2] / "openapi" / "benchmark-contract.yaml"


def _payload() -> dict[str, Any]:
    return build_result_payload(
        "5b3f0e1a-0000-4000-8000-000000000001",
        "2026-10-19T10:00:00+00:00",
        "2026-10-19T10:05:00+00:00",
        [make_result("m1"), make_result("m2", cold=False)],
        HOTEL,
        MACHINE,
        BACKEND,
    )


def test_build_result_payload_validates_against_the_contract() -> None:
    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    schema = {"$ref": "#/components/schemas/RunResult", "components": spec["components"]}

    jsonschema.validate(_payload(), schema)


def test_build_result_payload_carries_header_machine_and_one_record_per_request() -> None:
    payload = _payload()

    assert payload["schema_version"] == 2
    assert payload["machine"] == {
        "cpu": "Test CPU", "cpu_cores": 4, "memory_mb": 8192, "gpu": None, "os": "Linux",
    }  # fmt: skip
    assert payload["backend"] == {"name": "ollama", "version": "0.5.1"}
    assert payload["dataset"] == {"name": "d.csv", "sha256": "a" * 64, "rows": 10}
    assert [r["model"] for r in payload["results"]] == ["m1", "m2"]
    assert payload["results"][0]["schema_version"] == 2


def test_build_result_payload_keeps_the_notebook_field_names() -> None:
    record = _payload()["results"][0]

    for name in ("ttft_s", "total_s", "tokens_per_s", "system_ram_peak_mb", "gpu_vram_peak_mb"):
        assert name in record
