"""``GET /runs/{run_id}/summaries`` (MIL-007) against the service and the contract."""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest
import yaml
from starlette.testclient import TestClient

from nfbench.application.delivery import DeliveryService
from nfbench.application.run_service import RunService
from nfbench.domain.summaries import SummaryComparison, SummaryEntry
from nfbench.presentation.api import create_app
from tests.service_fakes import (
    HOTEL,
    FakeCatalog,
    FakeEpoch,
    FakeExecutor,
    FakeInspector,
    FakeSender,
    MemoryPendingStore,
)

TOKEN = "s3cret-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
CONTRACT = Path(__file__).resolve().parents[2] / "openapi" / "benchmark-contract.yaml"
GHOST = "5b3f0e1a-0000-4000-8000-000000000001"

ANSWER = json.dumps(
    {
        "summary": "Cancellations are high.",
        "overall_cancellation": {"rate": 0.37, "interpretation": "i"},
        "direct_customers": {"rate": 0.3, "interpretation": "i"},
        "agent_bookings": {"rate": 0.4, "interpretation": "i"},
        "key_findings": ["a"],
        "limitations": ["b"],
    }
)


class _Setup:
    def __init__(self) -> None:
        executor = FakeExecutor(answers={"m1": (ANSWER, "stop"), "m2": ("{", "length")})
        delivery = DeliveryService(FakeSender(), MemoryPendingStore(), FakeEpoch(1_792_404_000.0))
        self.service = RunService(
            FakeCatalog("m1", "m2"), executor, lambda: HOTEL, FakeInspector(), delivery
        )
        self.client = TestClient(create_app(self.service, TOKEN))

    def finished_run(self) -> str:
        started = self.client.post("/runs", headers=AUTH, json={"models": ["m1", "m2"]})
        self.service.tick()
        return str(started.json()["run_id"])


@pytest.fixture
def setup() -> _Setup:
    return _Setup()


@pytest.fixture(scope="module")
def contract() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    return loaded


def test_the_summaries_of_a_finished_run_are_returned(setup: _Setup) -> None:
    run_id = setup.finished_run()

    response = setup.client.get(f"/runs/{run_id}/summaries", headers=AUTH)

    assert response.status_code == 200
    body = response.json()
    assert body["run"] == 0
    assert body["runs"] == [0]
    assert body["message"] is None
    first, second = body["entries"]
    assert (first["model"], first["summary"], first["valid"]) == (
        "m1",
        "Cancellations are high.",
        True,
    )
    assert second["summary"] is None
    assert second["problem"] == "cut off at the maximum output tokens"
    assert second["raw_output"] == "{"


def test_a_repetition_that_the_result_does_not_have_gives_a_message_and_no_entries(
    setup: _Setup,
) -> None:
    run_id = setup.finished_run()

    body = setup.client.get(f"/runs/{run_id}/summaries?run=9", headers=AUTH).json()

    assert body["entries"] == []
    assert body["message"] == "This result has no such repetition."


@pytest.mark.parametrize("value", ["x", "-1", "1.5", ""])
def test_run_that_is_not_a_whole_number_is_400(setup: _Setup, value: str) -> None:
    run_id = setup.finished_run()

    response = setup.client.get(f"/runs/{run_id}/summaries?run={value}", headers=AUTH)

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"


def test_without_the_token_is_401(setup: _Setup) -> None:
    run_id = setup.finished_run()

    for headers in ({}, {"Authorization": "Bearer wrong"}):
        response = setup.client.get(f"/runs/{run_id}/summaries", headers=headers)
        assert response.status_code == 401
        assert response.json()["code"] == "unauthorized"


def test_an_unknown_run_is_404(setup: _Setup) -> None:
    response = setup.client.get(f"/runs/{GHOST}/summaries", headers=AUTH)

    assert response.status_code == 404
    assert response.json()["code"] == "run_not_found"


def test_a_run_that_has_no_result_yet_is_409(setup: _Setup) -> None:
    started = setup.client.post("/runs", headers=AUTH, json={"models": ["m1"]})

    response = setup.client.get(f"/runs/{started.json()['run_id']}/summaries", headers=AUTH)

    assert response.status_code == 409
    assert response.json()["code"] == "result_not_ready"


def test_the_contract_documents_the_route(contract: dict[str, Any]) -> None:
    operation = contract["paths"]["/runs/{run_id}/summaries"]["get"]

    assert set(operation["responses"]) == {"200", "400", "401", "404", "409"}
    assert "benchmark-service" in operation["tags"]
    assert "security" not in operation
    assert [p["name"] for p in operation["parameters"]] == ["run_id", "run"]


def test_the_schemas_of_the_contract_have_the_fields_of_the_service(
    contract: dict[str, Any],
) -> None:
    schemas = contract["components"]["schemas"]

    for name, kind in (("SummaryEntry", SummaryEntry), ("SummaryComparison", SummaryComparison)):
        documented = set(schemas[name]["properties"])
        assert documented == {f.name for f in fields(kind)}
        assert set(schemas[name]["required"]) == documented


def test_a_response_has_exactly_the_documented_fields(
    setup: _Setup, contract: dict[str, Any]
) -> None:
    run_id = setup.finished_run()
    body = setup.client.get(f"/runs/{run_id}/summaries", headers=AUTH).json()
    schemas = contract["components"]["schemas"]

    assert set(body) == set(schemas["SummaryComparison"]["properties"])
    for entry in body["entries"]:
        assert set(entry) == set(schemas["SummaryEntry"]["properties"])
