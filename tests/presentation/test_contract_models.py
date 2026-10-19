"""The model routes against ``openapi/benchmark-contract.yaml`` (ADR-0005)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from nfbench.domain.service import MODEL_NAME_PATTERN, PullState

CONTRACT = Path(__file__).resolve().parents[2] / "openapi" / "benchmark-contract.yaml"


@pytest.fixture(scope="module")
def contract() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    return loaded


@pytest.mark.parametrize(
    ("path", "method", "statuses"),
    [
        ("/models", "post", {"202", "400", "401", "409"}),
        ("/models/pulls/{pull_id}", "get", {"200", "401", "404"}),
        ("/models/{name}", "delete", {"204", "400", "401", "404", "409", "502"}),
    ],
)
def test_the_contract_documents_the_status_codes_of_the_model_routes(
    contract: dict[str, Any], path: str, method: str, statuses: set[str]
) -> None:
    assert set(contract["paths"][path][method]["responses"]) == statuses


def test_every_model_route_needs_the_token_and_none_overrides_the_default(
    contract: dict[str, Any],
) -> None:
    for path, method in [
        ("/models", "post"),
        ("/models/pulls/{pull_id}", "get"),
        ("/models/{name}", "delete"),
    ]:
        operation = contract["paths"][path][method]
        assert "security" not in operation
        assert "benchmark-service" in operation["tags"]


def test_the_listing_of_models_is_unchanged(contract: dict[str, Any]) -> None:
    assert set(contract["paths"]["/models"]["get"]["responses"]) == {"200", "401"}


def test_the_pull_states_of_the_contract_are_the_states_of_the_service(
    contract: dict[str, Any],
) -> None:
    documented = contract["components"]["schemas"]["PullStatus"]["properties"]["state"]["enum"]

    assert documented == [state.value for state in PullState]


def test_the_name_pattern_of_the_contract_is_the_pattern_of_the_service(
    contract: dict[str, Any],
) -> None:
    schema = contract["components"]["schemas"]["PullModel"]["properties"]["name"]

    assert schema["pattern"] == MODEL_NAME_PATTERN
    assert re.fullmatch(schema["pattern"], "phi4-mini:latest") is not None


def test_the_version_of_the_contract_is_one_point_one(contract: dict[str, Any]) -> None:
    assert contract["info"]["version"] == "1.1.0"
