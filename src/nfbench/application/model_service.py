"""Adding and deleting models of the model server (ADR-0005): validate, pull, delete."""

from __future__ import annotations

import logging
import re
import threading
import uuid
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import replace

from nfbench.application.ports import ModelAdmin, ModelCatalog, ModelUseGuard
from nfbench.domain.errors import (
    BackendError,
    InvalidModelNameError,
    ModelAlreadyInstalledError,
    ModelNotFoundError,
    PullActiveError,
    PullNotFoundError,
)
from nfbench.domain.service import (
    MAX_KEPT_PULLS,
    MAX_MODEL_NAME_LENGTH,
    MODEL_NAME_PATTERN,
    PullState,
    PullStatus,
)

logger = logging.getLogger(__name__)

_NAME = re.compile(MODEL_NAME_PATTERN)
LATEST_TAG = "latest"


def _start_thread(work: Callable[[], None]) -> None:
    threading.Thread(target=work, name="model-pull", daemon=True).start()


class ModelService:
    """One pull at a time with progress kept for the last pulls; deletes models that no run uses."""

    def __init__(
        self,
        catalog: ModelCatalog,
        admin: ModelAdmin,
        guard: ModelUseGuard,
        start: Callable[[Callable[[], None]], None] = _start_thread,
        new_id: Callable[[], str] = lambda: str(uuid.uuid4()),
    ) -> None:
        self._catalog = catalog
        self._admin = admin
        self._guard = guard
        self._start = start
        self._new_id = new_id
        self._lock = threading.Lock()
        self._pulls: OrderedDict[str, PullStatus] = OrderedDict()

    def start_pull(self, name: str) -> PullStatus:
        """Queue the pull of a model and return at once; raise on a wrong name or an active pull."""
        model = self._valid_name(name)
        if self._installed_name(model) is not None:
            raise ModelAlreadyInstalledError(f"model '{model}' is already installed")
        with self._lock:
            if any(s.state in (PullState.QUEUED, PullState.PULLING) for s in self._pulls.values()):
                raise PullActiveError("a pull is active; wait until it ends")
            status = PullStatus(self._new_id(), model, PullState.QUEUED)
            self._pulls[status.pull_id] = status
            while len(self._pulls) > MAX_KEPT_PULLS:
                self._pulls.popitem(last=False)
        self._start(lambda: self._run_pull(status.pull_id))
        return status

    def pull_status(self, pull_id: str) -> PullStatus:
        """The state of a pull."""
        with self._lock:
            try:
                return self._pulls[pull_id]
            except KeyError as error:
                raise PullNotFoundError(pull_id) from error

    def list_pulls(self) -> tuple[PullStatus, ...]:
        """The downloads that the service keeps, newest first (ADR-0006)."""
        with self._lock:
            return tuple(reversed(self._pulls.values()))

    def delete(self, name: str) -> None:
        """Delete an installed model; raise when it is not installed or a run uses it."""
        model = self._valid_name(name)
        installed = self._installed_name(model)
        if installed is None:
            raise ModelNotFoundError(f"model '{model}' is not installed")
        if not self._guard.delete_if_unused(installed, lambda: self._admin.delete(installed)):
            raise ModelNotFoundError(f"model '{model}' is not installed")

    def _run_pull(self, pull_id: str) -> None:
        status = self.pull_status(pull_id)
        self._set(pull_id, state=PullState.PULLING)
        try:
            self._admin.pull(status.model, lambda percent: self._set(pull_id, percent=percent))
        except BackendError as error:
            logger.warning("the pull of %s failed: %s", status.model, error)
            self._set(pull_id, state=PullState.FAILED, error=str(error) or "the pull failed")
        except Exception as error:  # a defect must end the pull, not leave it pulling for ever
            logger.exception("the pull of %s failed", status.model)
            self._set(pull_id, state=PullState.FAILED, error=f"unexpected error: {error}")
        else:
            self._set(pull_id, state=PullState.DONE, percent=100)

    def _set(self, pull_id: str, **changes: object) -> None:
        with self._lock:
            current = self._pulls.get(pull_id)
            if current is not None:
                self._pulls[pull_id] = replace(current, **changes)  # type: ignore[arg-type]

    @staticmethod
    def _valid_name(name: str) -> str:
        model = name.strip() if isinstance(name, str) else ""
        if not model or len(model) > MAX_MODEL_NAME_LENGTH or _NAME.fullmatch(model) is None:
            raise InvalidModelNameError("the name is not the name of an Ollama model")
        return model

    def _installed_name(self, model: str) -> str | None:
        """The name as the server lists it: itself, or ``name:latest`` for a name without a tag."""
        installed = set(self._catalog.installed_models())
        if model in installed:
            return model
        if ":" not in model and f"{model}:{LATEST_TAG}" in installed:
            return f"{model}:{LATEST_TAG}"
        return None
