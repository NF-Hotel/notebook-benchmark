"""CSV discovery, loading and validation (polars)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from nfbench.domain.errors import DatasetError
from nfbench.domain.models import ColumnMapping, DatasetInfo

_TRUE = {"1", "1.0", "true", "t", "yes", "y", "canceled", "cancelled"}
_FALSE = {"0", "0.0", "false", "f", "no", "n", "not_canceled", "not canceled"}
_NO_AGENT = {"", "null", "na", "n/a", "nan", "none"}


@dataclass(frozen=True, slots=True)
class LoadedDataset:
    """A validated CSV: the frame plus its identity."""

    frame: pl.DataFrame
    info: DatasetInfo
    mapping: ColumnMapping


def discover_csvs(root: Path) -> list[Path]:
    """All ``*.csv`` files below ``root`` (empty list when the folder does not exist)."""
    return sorted(root.rglob("*.csv")) if root.is_dir() else []


def file_sha256(path: Path) -> str:
    """SHA-256 of the file contents, identifying the exact dataset version."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canceled_flags(frame: pl.DataFrame, column: str) -> pl.Series:
    """Boolean series (null = missing) from a 1/0, true/false or yes/no column.

    Raises ``DatasetError`` if non-empty values are not recognised.
    """
    text = frame.get_column(column).cast(pl.String).str.strip_chars().str.to_lowercase()
    flags = text.replace_strict(
        {**dict.fromkeys(_TRUE, True), **dict.fromkeys(_FALSE, False)},
        default=None,
        return_dtype=pl.Boolean,
    )
    unknown = text.is_not_null() & (text != "") & flags.is_null()
    if unknown.any():
        examples = text.filter(unknown).unique().head(3).to_list()
        raise DatasetError(
            f"column '{column}' has values that are not 0/1 or true/false: {examples}"
        )
    return flags


def direct_flags(frame: pl.DataFrame, column: str) -> pl.Series:
    """True where a booking has no agent (null, empty, 'NULL', 'NA', ...)."""
    text = frame.get_column(column).cast(pl.String).str.strip_chars().str.to_lowercase()
    return text.is_null() | text.is_in(list(_NO_AGENT))


def load_dataset(path: Path, mapping: ColumnMapping | None = None) -> LoadedDataset:
    """Read and validate a hotel-booking CSV; raises ``DatasetError`` with a readable message."""
    mapping = mapping or ColumnMapping()
    if not path.is_file():
        raise DatasetError(f"file not found: {path}")
    try:
        frame = pl.read_csv(path, infer_schema_length=None)
    except (pl.exceptions.PolarsError, UnicodeDecodeError) as exc:
        raise DatasetError(f"cannot read '{path.name}' as CSV: {exc}") from exc
    if frame.width == 0 or frame.height == 0:
        raise DatasetError(f"'{path.name}' contains no data rows")
    missing = [c for c in (mapping.canceled, mapping.agent) if c not in frame.columns]
    if missing:
        raise DatasetError(
            f"required column(s) {missing} not found; available: {', '.join(frame.columns)}"
        )
    canceled_flags(frame, mapping.canceled)  # validates the values
    info = DatasetInfo(
        name=path.name,
        path=str(path),
        sha256=file_sha256(path),
        rows=frame.height,
        columns=tuple(frame.columns),
        dtypes={name: str(dtype) for name, dtype in frame.schema.items()},
        missing={name: frame.get_column(name).null_count() for name in frame.columns},
    )
    return LoadedDataset(frame, info, mapping)
