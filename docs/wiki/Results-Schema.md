# Results Schema

`output/results.jsonl`: one JSON object per request, `schema_version` 2. Rows without it are legacy v1 (deterministic tasks only) and are still read.

| Group | Fields |
|---|---|
| Identity | `timestamp`, `session_id`, `backend`, `model`, `task_id`, `category`, `analysis_type`, `run`, `cold` |
| Config | `temperature`, `max_tokens`, `runs`, `prompt_version` |
| Dataset | `dataset`, `dataset_hash` (SHA-256), `dataset_rows` |
| Metrics | `ttft_s`, `total_s`, `completion_tokens`, `prompt_tokens`, `tokens_per_s`, `tokens_estimated`, `finish_reason` |
| Resources (MB) | `system_ram_{before,after,peak}_mb`, `gpu_vram_{before,after,peak}_mb` |
| Outcome | `passed`, `response_valid`, `validation_error`, `output`, `error` |
