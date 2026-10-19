from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import pytest
from starlette.testclient import TestClient

from nfbench.application.delivery import DeliveryService
from nfbench.application.model_service import ModelService
from nfbench.application.run_service import RunService
from nfbench.domain.errors import BackendError
from nfbench.domain.service import StartRunRequest
from nfbench.presentation.api import create_app
from tests.service_fakes import (
    HOTEL,
    FakeCatalog,
    FakeEpoch,
    FakeExecutor,
    FakeInspector,
    FakeModelAdmin,
    FakeSender,
    MemoryPendingStore,
)

TOKEN = "s3cret-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@dataclass
class _World:
    client: TestClient
    runs: RunService
    admin: FakeModelAdmin
    catalog: FakeCatalog
    pending: list[Callable[[], None]] = field(default_factory=list)

    def finish_pulls(self) -> None:
        while self.pending:
            self.pending.pop(0)()


@pytest.fixture
def world() -> _World:
    catalog = FakeCatalog("m1:latest", "m2")
    delivery = DeliveryService(FakeSender(), MemoryPendingStore(), FakeEpoch(1_792_404_000.0))
    runs = RunService(catalog, FakeExecutor(), lambda: HOTEL, FakeInspector(), delivery)
    admin = FakeModelAdmin(catalog)
    pending: list[Callable[[], None]] = []
    models = ModelService(catalog, admin, runs, start=pending.append)
    return _World(
        TestClient(create_app(runs, TOKEN, model_service=models)), runs, admin, catalog, pending
    )


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/models"),
        ("get", "/models/pulls/some-id"),
        ("delete", "/models/m1:latest"),
        ("get", "/models/pulls"),
        ("get", "/runs"),
    ],
)
def test_model_routes_without_the_token_are_401(world: _World, method: str, path: str) -> None:
    response = world.client.request(method, path)

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


@pytest.mark.parametrize("method", ["post", "delete"])
def test_model_routes_with_a_wrong_token_are_401(world: _World, method: str) -> None:
    response = world.client.request(
        method,
        "/models/m1:latest" if method == "delete" else "/models",
        headers={"Authorization": "Bearer wrong"},
    )

    assert response.status_code == 401


def test_health_stays_open(world: _World) -> None:
    assert world.client.get("/health").status_code == 200


def test_a_pull_goes_from_queued_to_done_and_the_model_is_listed(world: _World) -> None:
    response = world.client.post("/models", json={"name": "phi4-mini"}, headers=AUTH)

    assert response.status_code == 202
    body = response.json()
    assert (body["model"], body["state"], body["percent"], body["error"]) == (
        "phi4-mini",
        "queued",
        None,
        None,
    )
    first = world.client.get(f"/models/pulls/{body['pull_id']}", headers=AUTH).json()
    world.finish_pulls()
    last = world.client.get(f"/models/pulls/{body['pull_id']}", headers=AUTH)
    assert first["state"] == "queued"
    assert last.status_code == 200
    assert (last.json()["state"], last.json()["percent"]) == ("done", 100)
    assert "phi4-mini" in world.client.get("/models", headers=AUTH).json()["models"]


def test_a_failed_pull_shows_its_reason(world: _World) -> None:
    world.admin.fail_with = "pull model manifest: file does not exist"
    pull_id = world.client.post("/models", json={"name": "nope"}, headers=AUTH).json()["pull_id"]

    world.finish_pulls()

    body = world.client.get(f"/models/pulls/{pull_id}", headers=AUTH).json()
    assert body["state"] == "failed"
    assert "file does not exist" in body["error"]
    assert "nope" not in world.client.get("/models", headers=AUTH).json()["models"]


@pytest.mark.parametrize("body", [{"name": "../x"}, {"name": ""}, {"name": 5}, {}, [1], "x"])
def test_post_models_an_invalid_name_is_400(world: _World, body: object) -> None:
    response = world.client.post("/models", json=body, headers=AUTH)

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_model_name"


def test_post_models_a_body_that_is_not_json_is_400(world: _World) -> None:
    response = world.client.post("/models", content=b"{nope", headers=AUTH)

    assert (response.status_code, response.json()["code"]) == (400, "invalid_request")


def test_post_models_an_installed_model_is_409(world: _World) -> None:
    response = world.client.post("/models", json={"name": "m1"}, headers=AUTH)

    assert (response.status_code, response.json()["code"]) == (409, "already_installed")


def test_post_models_while_a_pull_is_active_is_409(world: _World) -> None:
    world.client.post("/models", json={"name": "phi4-mini"}, headers=AUTH)

    response = world.client.post("/models", json={"name": "qwen2.5:7b"}, headers=AUTH)

    assert (response.status_code, response.json()["code"]) == (409, "pull_active")


def test_get_pull_unknown_id_is_404(world: _World) -> None:
    response = world.client.get("/models/pulls/nope", headers=AUTH)

    assert (response.status_code, response.json()["code"]) == (404, "pull_not_found")


def test_delete_an_installed_model_is_204_and_it_is_no_longer_listed(world: _World) -> None:
    response = world.client.delete("/models/m2", headers=AUTH)

    assert response.status_code == 204
    assert response.content == b""
    assert world.client.get("/models", headers=AUTH).json()["models"] == ["m1:latest"]


def test_delete_a_name_with_a_tag_and_a_path_reaches_the_service(world: _World) -> None:
    world.catalog.models = ("hf.co/user/model:Q4_K_M",)

    response = world.client.delete("/models/hf.co/user/model:Q4_K_M", headers=AUTH)

    assert response.status_code == 204
    assert world.admin.deleted == ["hf.co/user/model:Q4_K_M"]


def test_delete_an_unknown_model_is_404(world: _World) -> None:
    response = world.client.delete("/models/phi4-mini", headers=AUTH)

    assert (response.status_code, response.json()["code"]) == (404, "model_not_found")


def test_delete_a_model_that_a_queued_run_names_is_409_and_it_stays(world: _World) -> None:
    world.runs.start(StartRunRequest(("m2",)))

    response = world.client.delete("/models/m2", headers=AUTH)

    assert (response.status_code, response.json()["code"]) == (409, "model_in_use")
    assert world.admin.deleted == []
    assert "m2" in world.client.get("/models", headers=AUTH).json()["models"]


def test_delete_a_model_of_a_finished_run_is_allowed(world: _World) -> None:
    world.runs.start(StartRunRequest(("m2",)))
    world.runs.tick()

    assert world.client.delete("/models/m2", headers=AUTH).status_code == 204


def test_delete_an_invalid_name_is_400(world: _World) -> None:
    response = world.client.delete("/models/a b", headers=AUTH)

    assert (response.status_code, response.json()["code"]) == (400, "invalid_model_name")


def test_delete_when_ollama_fails_is_502(world: _World) -> None:
    world.admin.delete_error = BackendError("Ollama could not be reached")

    response = world.client.delete("/models/m2", headers=AUTH)

    assert (response.status_code, response.json()["code"]) == (502, "model_server_error")


def test_the_run_routes_still_work_next_to_the_model_routes(world: _World) -> None:
    response = world.client.post("/runs", json={"models": ["m2"]}, headers=AUTH)

    assert response.status_code == 202


def test_get_runs_with_no_run_is_200_and_an_empty_list(world: _World) -> None:
    response = world.client.get("/runs", headers=AUTH)

    assert response.status_code == 200
    assert response.json() == {"runs": []}


def test_get_runs_lists_the_runs_newest_first_and_follows_a_change_of_state(world: _World) -> None:
    first = world.client.post("/runs", json={"models": ["m1:latest"]}, headers=AUTH).json()
    second = world.client.post("/runs", json={"models": ["m2"]}, headers=AUTH).json()

    before = world.client.get("/runs", headers=AUTH).json()["runs"]
    world.runs.tick()
    after = world.client.get("/runs", headers=AUTH).json()["runs"]

    assert [run["run_id"] for run in before] == [second["run_id"], first["run_id"]]
    assert [run["state"] for run in before] == ["queued", "queued"]
    assert after[1]["state"] == "done"
    assert set(after[0]) == set(first)  # the fields of GET /runs/{run_id}


def test_get_pulls_with_no_pull_is_200_and_an_empty_list(world: _World) -> None:
    response = world.client.get("/models/pulls", headers=AUTH)

    assert response.status_code == 200
    assert response.json() == {"pulls": []}


def test_get_pulls_lists_the_pulls_newest_first_and_follows_a_change_of_state(
    world: _World,
) -> None:
    started = world.client.post("/models", json={"name": "phi4-mini"}, headers=AUTH).json()

    before = world.client.get("/models/pulls", headers=AUTH).json()["pulls"]
    world.finish_pulls()
    after = world.client.get("/models/pulls", headers=AUTH).json()["pulls"]

    assert [(p["pull_id"], p["state"]) for p in before] == [(started["pull_id"], "queued")]
    assert [(p["pull_id"], p["state"], p["percent"]) for p in after] == [
        (started["pull_id"], "done", 100)
    ]
    assert set(after[0]) == set(started)  # the fields of GET /models/pulls/{pull_id}


def test_get_pulls_is_not_taken_for_a_pull_id(world: _World) -> None:
    assert world.client.get("/models/pulls/nope", headers=AUTH).status_code == 404
    assert world.client.get("/models/pulls", headers=AUTH).status_code == 200
