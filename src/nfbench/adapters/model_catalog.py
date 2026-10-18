"""The installed models of a model server, read through its chat backend."""

from __future__ import annotations

from nfbench.application.ports import ChatBackend


class BackendModelCatalog:
    """Lists what the server lists; an unavailable server has no models."""

    def __init__(self, backend: ChatBackend) -> None:
        self._backend = backend

    def installed_models(self) -> tuple[str, ...]:
        """The model names, empty when the server is down."""
        status = self._backend.check()
        return status.models if status.available else ()
