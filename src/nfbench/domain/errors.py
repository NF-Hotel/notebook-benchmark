"""Domain errors."""

from __future__ import annotations


class BackendError(Exception):
    """A model server could not be reached or returned an unusable response."""


class DatasetError(Exception):
    """A dataset file is missing, unreadable, empty or lacks required columns."""


class InvalidRunRequestError(Exception):
    """A request to start a run is empty, out of range or names a model twice."""


class ModelNotInstalledError(InvalidRunRequestError):
    """A requested model is not installed in the model server."""


class QueueFullError(Exception):
    """A run is active and the waiting queue is full."""


class RunNotFoundError(Exception):
    """No run has the given id."""


class InvalidModelNameError(Exception):
    """A model name does not look like the name of an Ollama model (ADR-0005)."""


class ModelAlreadyInstalledError(Exception):
    """The model to pull is already installed."""


class PullActiveError(Exception):
    """A pull is queued or running; one pull at a time (ADR-0005)."""


class PullNotFoundError(Exception):
    """No pull has the given id."""


class ModelNotFoundError(Exception):
    """The model to delete is not installed."""


class ModelInUseError(Exception):
    """A queued or running benchmark run names the model, so it is not deleted."""
