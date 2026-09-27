"""Composition root: the only module that wires concrete implementations together."""

from __future__ import annotations

from pathlib import Path

from nfbench.adapters.backends import OpenAICompatibleBackend, default_backends
from nfbench.adapters.result_store import DEFAULT_RESULTS_PATH, JsonlResultStore
from nfbench.application.benchmark import BenchmarkController
from nfbench.infrastructure.resources import ThreadedResourceMonitor

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
