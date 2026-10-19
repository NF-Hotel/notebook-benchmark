"""The dataset and its deterministic summary for a run of the service."""

from __future__ import annotations

from pathlib import Path

from nfbench.adapters.datasets import load_dataset
from nfbench.adapters.hotel_analysis import analyse
from nfbench.application.benchmark import HotelInput


class DatasetHotelInput:
    """Loads the configured CSV and computes the facts the models interpret."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def __call__(self) -> HotelInput:
        """Raise ``DatasetError`` when the file is missing or unusable."""
        dataset = load_dataset(self._path)
        return HotelInput(dataset.info, analyse(dataset.frame, dataset.mapping))
