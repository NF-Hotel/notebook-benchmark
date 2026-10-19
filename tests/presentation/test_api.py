from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from nfbench.application.delivery import DeliveryService
from nfbench.application.run_service import RunService
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


@pytest.fixture
def client() -> TestClient:
    delivery = DeliveryService(FakeSender(), MemoryPendingStore(), FakeEpoch(1_792_404_000.0))
    service = RunService(
        FakeCatalog("m1", "m2"), FakeExecutor(), lambda: HOTEL, FakeInspector(), delivery
    )
    return TestClient(create_app(service, TOKEN))


def test_health_needs_no_token(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", "/models"), ("post", "/runs"), ("get", "/runs/5b3f0e1a-0000-4000-8000-000000000001")],
)
def test_protected_endpoint_without_token_is_401(
    client: TestClient, method: str, path: str
) -> None:
    response = client.request(method, path)

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


@pytest.mark.parametrize("header", ["Bearer wrong", "Basic abc", "s3cret-token", "Bearer "])
def test_protected_endpoint_with_a_wrong_token_is_401(client: TestClient, header: str) -> None:
    response = client.get("/models", headers={"Authorization": header})

    assert response.status_code == 401


def test_models_lists_the_installed_models(client: TestClient) -> None:
    response = client.get("/models", headers=AUTH)

    assert response.status_code == 200
    assert response.json() == {"models": ["m1", "m2"]}


def test_start_run_returns_202_with_a_queued_run(client: TestClient) -> None:
    response = client.post("/runs", json={"models": ["m1"]}, headers=AUTH)

    body = response.json()
    assert response.status_code == 202
    assert body["state"] == "queued"
    assert body["delivery"] == "not_ready"
    assert body["models"] == ["m1"]


def test_get_run_returns_the_state_of_a_started_run(client: TestClient) -> None:
    run_id = client.post("/runs", json={"models": ["m1"]}, headers=AUTH).json()["run_id"]

    response = client.get(f"/runs/{run_id}", headers=AUTH)

    assert response.status_code == 200
    assert response.json()["run_id"] == run_id


def test_get_run_unknown_id_is_404(client: TestClient) -> None:
    response = client.get("/runs/5b3f0e1a-0000-4000-8000-000000000001", headers=AUTH)

    assert response.status_code == 404
    assert response.json()["code"] == "run_not_found"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"models": []},
        {"models": "m1"},
        {"models": [1]},
        {"models": ["m1"], "runs": "two"},
        {"models": ["m1"], "runs": 9},
        {"models": ["m1"], "hotel_analysis": "yes"},
        {"models": ["m1"], "hotel_analysis": False, "deterministic_tasks": False},
    ],
)
def test_start_run_invalid_body_is_400(client: TestClient, body: dict[str, object]) -> None:
    response = client.post("/runs", json=body, headers=AUTH)

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"


def test_start_run_body_that_is_not_json_is_400(client: TestClient) -> None:
    response = client.post("/runs", content=b"{oops", headers=AUTH)

    assert response.status_code == 400


def test_start_run_model_not_installed_is_400(client: TestClient) -> None:
    response = client.post("/runs", json={"models": ["missing"]}, headers=AUTH)

    assert response.status_code == 400
    assert response.json()["code"] == "model_not_installed"


def test_start_run_third_waiting_run_is_429_with_retry_after(client: TestClient) -> None:
    client.post("/runs", json={"models": ["m1"]}, headers=AUTH)
    client.post("/runs", json={"models": ["m1"]}, headers=AUTH)

    response = client.post("/runs", json={"models": ["m1"]}, headers=AUTH)

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "30"
    assert response.json()["code"] == "queue_full"
