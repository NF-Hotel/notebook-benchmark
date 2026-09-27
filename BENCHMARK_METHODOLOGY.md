# Benchmark methodology

This document states exactly what is measured and what is not. Nothing here ranks models.

## What is benchmarked

Local LLMs served by Ollama or LM Studio (OpenAI-compatible `/v1/chat/completions`, streaming).
Two workloads:

1. **Hotel cancellation analysis** – the model receives a deterministic statistical summary of a
   CSV and answers in a fixed JSON structure.
2. **Deterministic tasks** (optional) – the five short prompts from `domain/tasks.py`, each with a
   simple substring/callable check.

## Measurements

| Metric | Definition |
|---|---|
| `ttft_s` | time of first streamed non-empty piece of text (answer **or** reasoning) minus request start |
| `total_s` | time when the stream ends minus request start |
| `completion_tokens` | `usage.completion_tokens` from the server when provided; otherwise the number of streamed chunks (`tokens_estimated = true`). Chunks are not guaranteed to equal tokens, so the fallback is approximate |
| `prompt_tokens` | `usage.prompt_tokens` when provided, else null |
| `tokens_per_s` | `completion_tokens / (end - first_token_time)`; null if there is no first token or no positive generation time. Excludes the wait before the first token, includes reasoning tokens |
| `passed` | deterministic tasks only: result of the task's check; null when the task has none. **Hotel analysis has no pass/fail** |
| `response_valid` | hotel analysis only: the response parsed as JSON and has the required fields with the right types. This is a format check, not a quality or correctness score |

Timestamps use `time.perf_counter()`. Times include local HTTP overhead on `localhost`.

## Cold vs warm

The first request of each (backend, model) in a benchmark session is flagged `cold = true`.
It may include model loading. If the model was already resident in memory the request is
effectively warm; the flag records the *position*, not a verified load event. Reports show
cold and warm separately; warm statistics exclude cold requests.

## Resources

Sampled every ~0.25 s in a background thread during each request:

* **System RAM** – system-wide used physical memory (`psutil.virtual_memory().used`), MB.
  System-wide because the model runs inside the Ollama / LM Studio process, not this one.
  Other applications running at the same time change this value.
* **GPU VRAM** – `nvidia-smi --query-gpu=memory.used`, summed over GPUs, MB. Only NVIDIA GPUs
  with `nvidia-smi` on the PATH are supported; otherwise the value is null ("unavailable").

`before` = sample at request start, `after` = sample at request end, `peak` = maximum sample seen.
The peak can miss spikes shorter than the sampling interval. Values are *totals on the machine*,
not the model's own footprint; compare `before`/`peak` differences with care.

## Configuration recorded with every result

temperature (default 0), max output tokens (default 2048), number of runs (default 1), prompt
version, dataset file name, SHA-256, row count, column mapping, backend and model, session id, timestamp.
Every model in a session gets the identical prompt and settings. A temperature of 0 reduces but
does not guarantee identical outputs across runs or servers.

## Dataset handling

Statistics are computed with Python (polars) from the whole CSV; the LLM sees only the summary.
Direct vs agent bookings are determined by the `agent` column: missing / empty / `NULL` = direct,
any other value = agent. Categorical breakdowns are limited to the largest groups (see the prompt)
so the prompt size stays bounded; the truncation is stated in the prompt.

## Interpreting results

* Speed numbers describe this machine, this server version, this quantisation, at this moment.
* Reasoning models spend tokens on thinking; with a small `max_tokens` they may return no final
  answer (`response_valid = false`). That is a measurement, not necessarily a defect.
* The hotel responses are shown side by side next to the ground-truth statistics so a reader can
  judge them. No automatic quality score or "best model" is produced.
* Small numbers of runs give no variance estimate; use `runs >= 3` before comparing close values.
