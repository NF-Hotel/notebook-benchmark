# Dataset

The expected schema follows the public "Hotel booking demand" dataset. The mapping is editable in the notebook.

| Required | Default column | Meaning |
|---|---|---|
| yes | `is_canceled` | 1/0 (also true/false, yes/no) |
| yes | `agent` | agent id; empty / `NULL` / `NA` = **direct** booking, any other value = **agent** booking |
| no | `hotel`, `market_segment`, `distribution_channel`, `deposit_type`, `customer_type` | categorical breakdowns |
| no | `lead_time`, `adr`, `booking_changes`, `previous_cancellations`, `total_of_special_requests`, `arrival_date_month` | binned breakdowns |

Optional columns that are absent are skipped and noted. Rows without a cancellation flag are excluded and noted. Only the 12 largest groups per dimension are listed (stated in the prompt).

Real CSVs stay in `data/` and are git-ignored; only `data/example/` is tracked.

The LLM never receives the CSV, only the computed statistics summary.
