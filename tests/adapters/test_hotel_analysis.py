from __future__ import annotations

import polars as pl
import pytest

from nfbench.adapters.hotel_analysis import analyse, group_stats
from nfbench.domain.models import Breakdown, ColumnMapping


def _frame() -> pl.DataFrame:
    # 10 bookings: 4 direct (1 canceled), 6 agent (3 canceled)
    return pl.DataFrame(
        {
            "is_canceled": [1, 0, 0, 0, 1, 1, 1, 0, 0, 0],
            "agent": ["NULL", "NULL", "NULL", "NULL", "9", "9", "14", "14", "240", "240"],
            "hotel": ["City"] * 6 + ["Resort"] * 4,
            "lead_time": [1, 5, 10, 40, 100, 200, 400, 3, 60, 8],
        }
    )


def _breakdown(summary_breakdowns: tuple[Breakdown, ...], dimension: str) -> Breakdown:
    return next(b for b in summary_breakdowns if b.dimension == dimension)


def test_analyse_overall_cancellation_counts_and_rate() -> None:
    summary = analyse(_frame())
    assert (summary.overall.bookings, summary.overall.cancellations) == (10, 4)
    assert summary.overall.rate == pytest.approx(0.4)


def test_analyse_direct_customers_rate() -> None:
    direct = analyse(_frame()).direct
    assert (direct.bookings, direct.cancellations) == (4, 1)
    assert direct.rate == pytest.approx(0.25)


def test_analyse_agent_bookings_rate() -> None:
    agent = analyse(_frame()).agent
    assert (agent.bookings, agent.cancellations) == (6, 3)
    assert agent.rate == pytest.approx(0.5)


def test_analyse_all_direct_gives_empty_agent_group_with_no_rate() -> None:
    frame = pl.DataFrame({"is_canceled": [1, 0], "agent": ["NULL", None]})
    summary = analyse(frame)
    assert summary.agent.bookings == 0
    assert summary.agent.rate is None
    assert summary.direct.rate == pytest.approx(0.5)


def test_analyse_excludes_rows_with_missing_cancellation_flag_and_notes_it() -> None:
    frame = pl.DataFrame({"is_canceled": [1, None, 0], "agent": ["1", "1", "NULL"]})
    summary = analyse(frame)
    assert summary.overall.bookings == 2
    assert any("1 rows without a cancellation flag" in n for n in summary.notes)


def test_analyse_skips_missing_optional_columns_and_notes_them() -> None:
    frame = pl.DataFrame({"is_canceled": [1, 0], "agent": ["1", "NULL"]})
    summary = analyse(frame)
    assert summary.breakdowns == ()
    assert any("'lead_time' not found" in n for n in summary.notes)


def test_analyse_categorical_breakdown_is_sorted_by_size() -> None:
    hotel = _breakdown(analyse(_frame()).breakdowns, "hotel")
    assert [(r.value, r.stats.bookings, r.stats.cancellations) for r in hotel.rows] == [
        ("City", 6, 3),
        ("Resort", 4, 1),
    ]


def test_analyse_lead_time_bins_keep_natural_order() -> None:
    lead = _breakdown(analyse(_frame()).breakdowns, "lead_time")
    assert [r.value for r in lead.rows] == [
        "0-7 days",
        "8-30 days",
        "31-90 days",
        "91-180 days",
        "181+ days",
    ]
    counts = {r.value: r.stats.bookings for r in lead.rows}
    assert counts == {
        "0-7 days": 3,
        "8-30 days": 2,
        "31-90 days": 2,
        "91-180 days": 1,
        "181+ days": 2,
    }


def test_analyse_limits_groups_per_dimension_and_reports_omitted() -> None:
    n = 20
    frame = pl.DataFrame(
        {"is_canceled": [0, 1] * (n // 2), "agent": ["1"] * n, "hotel": [f"h{i}" for i in range(n)]}
    )
    hotel = _breakdown(analyse(frame).breakdowns, "hotel")
    assert len(hotel.rows) == 12
    assert hotel.omitted_groups == 8


def test_analyse_uses_custom_mapping() -> None:
    frame = pl.DataFrame({"canc": ["yes", "no", "yes"], "broker": ["7", None, "8"]})
    summary = analyse(frame, ColumnMapping(canceled="canc", agent="broker", categorical=()))
    assert summary.overall.cancellations == 2
    assert summary.direct.bookings == 1
    assert summary.agent.bookings == 2


def test_group_stats_empty_group_has_no_rate() -> None:
    assert group_stats(0, 0).rate is None
