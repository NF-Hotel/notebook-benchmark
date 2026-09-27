"""Deterministic hotel-cancellation statistics computed with polars."""

from __future__ import annotations

import calendar

import polars as pl

from nfbench.adapters.datasets import canceled_flags, direct_flags
from nfbench.domain.models import (
    Breakdown,
    BreakdownRow,
    ColumnMapping,
    GroupStats,
    HotelSummary,
)

MAX_GROUPS_PER_DIMENSION = 12
_FLAG = "__canceled"
_MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}

# (upper bound inclusive, label); anything above the last bound gets the final label
_LEAD_TIME_BINS = ((7, "0-7 days"), (30, "8-30 days"), (90, "31-90 days"), (180, "91-180 days"))
_LEAD_TIME_LAST = "181+ days"


def group_stats(cancellations: int, bookings: int) -> GroupStats:
    """Stats for one group; the rate is None when the group is empty."""
    rate = cancellations / bookings if bookings else None
    return GroupStats(bookings, cancellations, rate)


def _stats(frame: pl.DataFrame) -> GroupStats:
    return group_stats(int(frame.get_column(_FLAG).sum()), frame.height)


def _breakdown_from_labels(
    frame: pl.DataFrame, dimension: str, labels: pl.Series, order: list[str] | None = None
) -> Breakdown:
    grouped = (
        frame.with_columns(labels.alias("__label"))
        .group_by("__label")
        .agg(pl.len().alias("n"), pl.col(_FLAG).sum().alias("c"))
    )
    rows = [
        BreakdownRow(str(label), group_stats(int(c), int(n))) for label, n, c in grouped.iter_rows()
    ]
    if order is not None:
        rank = {label: i for i, label in enumerate(order)}
        rows.sort(key=lambda r: rank.get(r.value, len(rank)))
        return Breakdown(dimension, tuple(rows))
    rows.sort(key=lambda r: (-r.stats.bookings, r.value))
    omitted = max(0, len(rows) - MAX_GROUPS_PER_DIMENSION)
    return Breakdown(dimension, tuple(rows[:MAX_GROUPS_PER_DIMENSION]), omitted)


def _categorical(frame: pl.DataFrame, column: str) -> Breakdown:
    labels = frame.get_column(column).cast(pl.String).fill_null("(missing)")
    return _breakdown_from_labels(frame, column, labels)


def _binned(
    frame: pl.DataFrame,
    column: str,
    bins: tuple[tuple[float, str], ...],
    last_label: str,
    dimension: str,
) -> Breakdown | None:
    values = frame.get_column(column).cast(pl.Float64, strict=False)
    known = frame.filter(values.is_not_null())
    if known.is_empty():
        return None
    known_values = known.get_column(column).cast(pl.Float64, strict=False)
    expr = pl.lit(last_label)
    for bound, label in reversed(bins):
        expr = pl.when(pl.col("__v") <= bound).then(pl.lit(label)).otherwise(expr)
    labels = known.with_columns(known_values.alias("__v")).select(expr.alias("l")).to_series()
    order = [label for _, label in bins] + [last_label]
    return _breakdown_from_labels(known, dimension, labels, order)


def _adr_bins(frame: pl.DataFrame, column: str) -> tuple[tuple[tuple[float, str], ...], str] | None:
    values = frame.get_column(column).cast(pl.Float64, strict=False).drop_nulls()
    if values.len() < 8:
        return None
    edges = sorted({round(float(values.quantile(q) or 0.0), 2) for q in (0.25, 0.5, 0.75)})
    if not edges:
        return None
    bins = tuple((edge, f"<= {edge:g}") for edge in edges)
    return bins, f"> {edges[-1]:g}"


def _month_breakdown(frame: pl.DataFrame, column: str) -> Breakdown | None:
    labels = frame.get_column(column).cast(pl.String).str.strip_chars().str.to_lowercase()
    if not labels.drop_nulls().is_in(list(_MONTHS)).all():
        return _categorical(frame, column)
    order = [calendar.month_name[m].lower() for m in range(1, 13)]
    return _breakdown_from_labels(frame, column, labels.fill_null("(missing)"), order)


def _count_bins(frame: pl.DataFrame, column: str, limits: tuple[int, ...]) -> Breakdown | None:
    """0, 1, ..., limit+ style buckets for count-like columns."""
    bins = tuple((float(n), str(n)) for n in limits[:-1])
    return _binned(frame, column, bins, f"{limits[-1]}+", column)


def _optional_breakdowns(
    frame: pl.DataFrame, mapping: ColumnMapping, notes: list[str]
) -> list[Breakdown]:
    found: list[Breakdown | None] = []

    def present(column: str | None) -> str | None:
        if column is None:
            return None
        if column in frame.columns:
            return column
        notes.append(f"column '{column}' not found; its breakdown was skipped")
        return None

    if col := present(mapping.lead_time):
        found.append(_binned(frame, col, _LEAD_TIME_BINS, _LEAD_TIME_LAST, col))
    if col := present(mapping.adr):
        bins = _adr_bins(frame, col)
        if bins:
            found.append(_binned(frame, col, bins[0], bins[1], f"{col} (quartile cut points)"))
    if col := present(mapping.booking_changes):
        found.append(_count_bins(frame, col, (0, 1, 2)))
    if col := present(mapping.previous_cancellations):
        found.append(_count_bins(frame, col, (0, 1)))
    if col := present(mapping.special_requests):
        found.append(_count_bins(frame, col, (0, 1, 2, 3)))
    if col := present(mapping.arrival_month):
        found.append(_month_breakdown(frame, col))
    return [b for b in found if b is not None]


def analyse(frame: pl.DataFrame, mapping: ColumnMapping | None = None) -> HotelSummary:
    """Overall / direct / agent cancellation statistics plus breakdowns.

    Rows whose cancellation flag is missing are excluded and noted. Optional columns that
    are absent are skipped and noted. ``mapping`` columns must exist (validated on load).
    """
    mapping = mapping or ColumnMapping()
    notes: list[str] = []
    flags = canceled_flags(frame, mapping.canceled)
    work = frame.with_columns(
        flags.alias(_FLAG), direct_flags(frame, mapping.agent).alias("__direct")
    )
    dropped = work.filter(pl.col(_FLAG).is_null()).height
    work = work.filter(pl.col(_FLAG).is_not_null())
    if dropped:
        notes.append(f"{dropped} rows without a cancellation flag were excluded")
    work = work.with_columns(pl.col(_FLAG).cast(pl.Int64))
    direct = work.filter(pl.col("__direct"))
    agent = work.filter(~pl.col("__direct"))
    breakdowns = [_categorical(work, col) for col in mapping.categorical if _has(work, col, notes)]
    breakdowns += _optional_breakdowns(work, mapping, notes)
    if any(b.omitted_groups for b in breakdowns):
        notes.append(f"only the {MAX_GROUPS_PER_DIMENSION} largest groups per dimension are listed")
    return HotelSummary(
        _stats(work), _stats(direct), _stats(agent), tuple(breakdowns), tuple(notes)
    )


def _has(frame: pl.DataFrame, column: str, notes: list[str]) -> bool:
    if column in frame.columns:
        return True
    notes.append(f"column '{column}' not found; its breakdown was skipped")
    return False
