from __future__ import annotations

from pathlib import Path

import pytest

from nfbench.adapters.hotel_input import DatasetHotelInput
from nfbench.adapters.model_catalog import BackendModelCatalog
from nfbench.domain.errors import DatasetError
from nfbench.domain.models import BackendStatus
from tests.fakes import FakeBackend

EXAMPLE = Path(__file__).resolve().parents[2] / "data" / "example" / "synthetic_hotel_bookings.csv"


def test_dataset_hotel_input_loads_info_and_summary_from_the_csv() -> None:
    hotel = DatasetHotelInput(EXAMPLE)()

    assert hotel.info.name == EXAMPLE.name
    assert len(hotel.info.sha256) == 64
    assert hotel.summary.overall.bookings == hotel.info.rows


def test_dataset_hotel_input_missing_file_raises_dataset_error(tmp_path: Path) -> None:
    with pytest.raises(DatasetError):
        DatasetHotelInput(tmp_path / "missing.csv")()


def test_backend_model_catalog_lists_the_models_of_an_available_backend() -> None:
    catalog = BackendModelCatalog(FakeBackend("ollama"))

    assert catalog.installed_models() == ("m1",)


class _DownBackend(FakeBackend):
    def check(self) -> BackendStatus:
        return BackendStatus(self.name, "fake://", False, (), "connection refused")


def test_backend_model_catalog_backend_down_lists_nothing() -> None:
    assert BackendModelCatalog(_DownBackend("ollama")).installed_models() == ()
