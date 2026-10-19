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
