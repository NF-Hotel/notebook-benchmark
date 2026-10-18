"""Build the body that is posted to the web API (openapi/benchmark-contract.yaml, RunResult)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from typing import Any

from nfbench.application.benchmark import HotelInput
from nfbench.application.prompts import HOTEL_PROMPT_VERSION
from nfbench.domain.models import SCHEMA_VERSION, RunResult
from nfbench.domain.service import BackendInfo, MachineInfo


def build_result_payload(
    run_id: str,
    started_at: str,
    finished_at: str,
    results: Sequence[RunResult],
    hotel: HotelInput,
    machine: MachineInfo,
    backend: BackendInfo,
) -> dict[str, Any]:  # Any: JSON body of the contract
    """The run header and one record per request, in the result schema of the notebook."""
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "prompt_version": HOTEL_PROMPT_VERSION,
        "dataset": {
            "name": hotel.info.name,
            "sha256": hotel.info.sha256,
            "rows": hotel.info.rows,
        },
        "machine": asdict(machine),
        "backend": asdict(backend),
        "results": [result.to_record() for result in results],
    }
