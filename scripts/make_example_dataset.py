"""Generate a SYNTHETIC hotel-booking CSV (public 'Hotel booking demand' column names).

The data is random with built-in effects; it says nothing about real hotels.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "example" / "synthetic_hotel_bookings.csv"
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]  # fmt: skip
COLUMNS = [
    "hotel", "is_canceled", "lead_time", "arrival_date_year", "arrival_date_month",
    "market_segment", "distribution_channel", "deposit_type", "customer_type", "agent",
    "booking_changes", "previous_cancellations", "total_of_special_requests", "adr",
]  # fmt: skip


def make_row(rng: random.Random) -> dict[str, object]:
    """One random booking; cancellation odds depend on agent, lead time, deposit, requests."""
    agent = rng.choice(["NULL", "NULL", "9", "9", "14", "240", "7"])
    lead = int(rng.expovariate(1 / 90))
    deposit = rng.choices(["No Deposit", "Non Refund", "Refundable"], [85, 13, 2])[0]
    requests = rng.choices([0, 1, 2, 3], [55, 30, 10, 5])[0]
    p = 0.18 + (0.15 if agent != "NULL" else 0.0) + min(lead, 300) / 900
    p += 0.35 if deposit == "Non Refund" else 0.0
    p -= 0.06 * requests
    return {
        "hotel": rng.choice(["City Hotel", "Resort Hotel"]),
        "is_canceled": int(rng.random() < max(0.02, min(p, 0.95))),
        "lead_time": lead,
        "arrival_date_year": rng.choice([2015, 2016, 2017]),
        "arrival_date_month": rng.choice(MONTHS),
        "market_segment": rng.choice(
            ["Online TA", "Offline TA/TO", "Direct", "Groups", "Corporate"]
        ),
        "distribution_channel": rng.choice(["TA/TO", "Direct", "Corporate"]),
        "deposit_type": deposit,
        "customer_type": rng.choices(["Transient", "Contract", "Group"], [75, 20, 5])[0],
        "agent": agent,
        "booking_changes": rng.choices([0, 1, 2, 3], [80, 13, 5, 2])[0],
        "previous_cancellations": rng.choices([0, 1, 2], [92, 6, 2])[0],
        "total_of_special_requests": requests,
        "adr": round(rng.uniform(40, 260), 2),
    }


def main() -> None:
    """Write 3000 rows with a fixed seed."""
    rng = random.Random(42)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(make_row(rng) for _ in range(3000))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
