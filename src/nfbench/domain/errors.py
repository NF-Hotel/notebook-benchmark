"""Domain errors."""

from __future__ import annotations


class BackendError(Exception):
    """A model server could not be reached or returned an unusable response."""


class DatasetError(Exception):
    """A dataset file is missing, unreadable, empty or lacks required columns."""
