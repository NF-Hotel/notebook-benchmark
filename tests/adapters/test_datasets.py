from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from nfbench.adapters.datasets import canceled_flags, direct_flags, discover_csvs, load_dataset
from nfbench.domain.errors import DatasetError
from nfbench.domain.models import ColumnMapping

CSV = "is_canceled,agent,hotel\n1,NULL,City\n0,9,City\n1,14,Resort\n0,,Resort\n"


def _write(tmp_path: Path, text: str, name: str = "d.csv") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_load_dataset_valid_csv_reports_shape_hash_and_missing(tmp_path: Path) -> None:
    loaded = load_dataset(_write(tmp_path, CSV))
    assert loaded.info.name == "d.csv"
    assert loaded.info.rows == 4
    assert loaded.info.columns == ("is_canceled", "agent", "hotel")
    assert len(loaded.info.sha256) == 64
    assert loaded.info.missing["agent"] == 1  # the empty cell; "NULL" text is not a null
    assert loaded.info.dtypes["hotel"] == "String"


def test_load_dataset_same_content_same_hash_different_content_different_hash(
    tmp_path: Path,
) -> None:
    a = load_dataset(_write(tmp_path, CSV, "a.csv"))
    b = load_dataset(_write(tmp_path, CSV, "b.csv"))
    c = load_dataset(_write(tmp_path, CSV + "1,3,City\n", "c.csv"))
    assert a.info.sha256 == b.info.sha256 != c.info.sha256


def test_load_dataset_missing_file_raises_readable_error(tmp_path: Path) -> None:
    with pytest.raises(DatasetError, match="file not found"):
        load_dataset(tmp_path / "nope.csv")


def test_load_dataset_empty_file_raises(tmp_path: Path) -> None:
    with pytest.raises(DatasetError, match="no data rows|cannot read"):
        load_dataset(_write(tmp_path, ""))


def test_load_dataset_header_only_raises(tmp_path: Path) -> None:
    with pytest.raises(DatasetError, match="no data rows"):
        load_dataset(_write(tmp_path, "is_canceled,agent\n"))


def test_load_dataset_missing_required_column_lists_available(tmp_path: Path) -> None:
    with pytest.raises(DatasetError, match=r"\['agent'\].*is_canceled"):
        load_dataset(_write(tmp_path, "is_canceled,hotel\n1,City\n"))


def test_load_dataset_malformed_csv_raises_dataset_error(tmp_path: Path) -> None:
    with pytest.raises(DatasetError):
        load_dataset(_write(tmp_path, 'is_canceled,agent\n1,"unterminated\n0,3,4,5\n'))


def test_load_dataset_unrecognised_cancel_values_raise(tmp_path: Path) -> None:
    with pytest.raises(DatasetError, match="not 0/1"):
        load_dataset(_write(tmp_path, "is_canceled,agent\nmaybe,1\n0,2\n"))


def test_load_dataset_respects_custom_column_mapping(tmp_path: Path) -> None:
    path = _write(tmp_path, "canc,broker\ntrue,7\nfalse,\n")
    loaded = load_dataset(path, ColumnMapping(canceled="canc", agent="broker"))
    assert loaded.info.rows == 2


def test_canceled_flags_accepts_common_encodings() -> None:
    frame = pl.DataFrame({"c": ["1", "0", "True", "no", None]})
    assert canceled_flags(frame, "c").to_list() == [True, False, True, False, None]


def test_direct_flags_classifies_agent_values() -> None:
    frame = pl.DataFrame({"agent": ["NULL", "9", "", None, " 240 ", "na"]})
    assert direct_flags(frame, "agent").to_list() == [True, False, True, True, False, True]


def test_direct_flags_works_for_numeric_agent_column() -> None:
    frame = pl.DataFrame({"agent": [9, None, 14]})
    assert direct_flags(frame, "agent").to_list() == [False, True, False]


def test_discover_csvs_finds_nested_files_and_tolerates_missing_folder(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    _write(tmp_path / "sub", CSV, "x.csv")
    _write(tmp_path, "not a csv", "notes.txt")
    assert [p.name for p in discover_csvs(tmp_path)] == ["x.csv"]
    assert discover_csvs(tmp_path / "absent") == []
