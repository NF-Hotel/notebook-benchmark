from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from nfbench.bootstrap import ServiceSettings, build_run_service, create_service_app

ENV = {
    "NFBENCH_API_TOKEN": "api",
    "NFBENCH_WEB_URL": "http://api:8080",
    "NFBENCH_WEB_TOKEN": "web",
}


def test_from_env_reads_tokens_address_and_defaults() -> None:
    settings = ServiceSettings.from_env(ENV)

    assert (settings.api_token, settings.web_url, settings.web_token) == (
        "api",
        "http://api:8080",
        "web",
    )
    assert settings.ollama_url == "http://localhost:11434"


def test_from_env_overrides_the_optional_settings() -> None:
    settings = ServiceSettings.from_env(
        {**ENV, "NFBENCH_OLLAMA_URL": "http://ollama:11434", "NFBENCH_DATA_DIR": "/data"}
    )

    assert settings.ollama_url == "http://ollama:11434"
    assert settings.data_dir == Path("/data")


@pytest.mark.parametrize("missing", sorted(ENV))
def test_from_env_missing_required_setting_fails_at_start(missing: str) -> None:
    env = {k: v for k, v in ENV.items() if k != missing}

    with pytest.raises(ValueError, match=missing):
        ServiceSettings.from_env(env)


def test_build_run_service_wires_without_touching_the_network(tmp_path: Path) -> None:
    settings = ServiceSettings.from_env({**ENV, "NFBENCH_DATA_DIR": str(tmp_path)})

    assert build_run_service(settings) is not None


def test_create_service_app_serves_health_and_guards_models(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for name, value in {**ENV, "NFBENCH_DATA_DIR": str(tmp_path)}.items():
        monkeypatch.setenv(name, value)

    with TestClient(create_service_app()) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/models").status_code == 401
