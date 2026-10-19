"""Composition root: the only module that wires concrete implementations together."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from starlette.applications import Starlette

from nfbench.adapters.backends import OpenAICompatibleBackend, default_backends
from nfbench.adapters.hotel_input import DatasetHotelInput
from nfbench.adapters.model_catalog import BackendModelCatalog
from nfbench.adapters.ollama_info import OllamaVersionReader
from nfbench.adapters.ollama_models import OllamaModelAdmin
from nfbench.adapters.pending_store import FilePendingStore
from nfbench.adapters.result_store import DEFAULT_RESULTS_PATH, JsonlResultStore
from nfbench.adapters.web_result_sender import WebResultSender
from nfbench.application.benchmark import BenchmarkController
from nfbench.application.delivery import DeliveryService
from nfbench.application.model_service import ModelService
from nfbench.application.run_service import RunService
from nfbench.infrastructure.machine import SystemMachineInspector
from nfbench.infrastructure.resources import ThreadedResourceMonitor
from nfbench.infrastructure.worker import BackgroundWorker
from nfbench.presentation.api import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"


def build_backends() -> dict[str, OpenAICompatibleBackend]:
    """Ollama and LM Studio adapters keyed by name."""
    return default_backends()


def build_store(path: Path = DEFAULT_RESULTS_PATH) -> JsonlResultStore:
    """The JSONL result store."""
    return JsonlResultStore(path)


def build_controller(store: JsonlResultStore) -> BenchmarkController:
    """Controller wired with the real backends and resource monitor."""
    return BenchmarkController(build_backends(), ThreadedResourceMonitor(), store)


@dataclass(frozen=True, slots=True)
class ServiceSettings:
    """The configuration of the benchmark service, read from its env file (ADR-0001)."""

    api_token: str
    web_url: str
    web_token: str
    ollama_url: str = "http://localhost:11434"
    dataset: Path = DATA_DIR / "example" / "synthetic_hotel_bookings.csv"
    data_dir: Path = OUTPUT_DIR / "service"

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> ServiceSettings:
        """Read the settings; a missing token or web address is an error at start, not later."""
        missing = [
            name
            for name in ("NFBENCH_API_TOKEN", "NFBENCH_WEB_URL", "NFBENCH_WEB_TOKEN")
            if not environ.get(name)
        ]
        if missing:
            raise ValueError("missing settings: " + ", ".join(missing))
        defaults = cls("", "", "")
        return cls(
            api_token=environ["NFBENCH_API_TOKEN"],
            web_url=environ["NFBENCH_WEB_URL"],
            web_token=environ["NFBENCH_WEB_TOKEN"],
            ollama_url=environ.get("NFBENCH_OLLAMA_URL", defaults.ollama_url),
            dataset=Path(environ.get("NFBENCH_DATASET", str(defaults.dataset))),
            data_dir=Path(environ.get("NFBENCH_DATA_DIR", str(defaults.data_dir))),
        )


def build_run_service(settings: ServiceSettings) -> RunService:
    """The run service wired with Ollama, the dataset, the pending store and the web sender."""
    backend = OpenAICompatibleBackend("ollama", settings.ollama_url.rstrip("/") + "/v1")
    store = JsonlResultStore(settings.data_dir / "results.jsonl")
    controller = BenchmarkController({"ollama": backend}, ThreadedResourceMonitor(), store)
    delivery = DeliveryService(
        WebResultSender(settings.web_url, settings.web_token),
        FilePendingStore(settings.data_dir),
    )
    inspector = SystemMachineInspector("ollama", OllamaVersionReader(settings.ollama_url))
    return RunService(
        BackendModelCatalog(backend),
        controller,
        DatasetHotelInput(settings.dataset),
        inspector,
        delivery,
    )


def create_service_app() -> Starlette:
    """ASGI factory: ``uvicorn --factory nfbench.bootstrap:create_service_app``."""
    settings = ServiceSettings.from_env(os.environ)
    service = build_run_service(settings)
    backend = OpenAICompatibleBackend("ollama", settings.ollama_url.rstrip("/") + "/v1")
    model_service = ModelService(
        BackendModelCatalog(backend), OllamaModelAdmin(settings.ollama_url), service
    )
    worker = BackgroundWorker(service.tick)

    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        service.restore()
        worker.start()
        try:
            yield
        finally:
            worker.stop()

    return create_app(service, settings.api_token, lifespan, model_service)
