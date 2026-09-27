# Implementation plan

Inspected state of the repository before this work (2026-09-27).

## 1–3. Current architecture, modules, existing functionality

Flat package `src/nfbench/`, no tests, no docs:

| Module | Responsibility |
|---|---|
| `backends.py` | `Backend(name, base_url)`; `list_models()`; constants `LM_STUDIO`, `OLLAMA`, `BACKENDS` |
| `runner.py` | `run_once()` streams `/chat/completions`, measures TTFT / total / tokens / tokens-per-s, `Result` dataclass, JSONL `save()` / pandas `load()` |
| `tasks.py` | five deterministic `Task`s with an optional `check` callable |
| `notebooks/benchmark.py` | marimo dashboard over the deterministic tasks (pandas + Altair) |

`src/nfbench/benchmark.py` is named in the request but **does not exist**; orchestration lived
in the notebook. `output/results.jsonl` holds 20 schema-v1 rows from earlier runs and must stay readable.

Repo rules (`.claude/agents/python-developer.md`): Clean Architecture layers, polars first,
ruff + `mypy --strict` + import-linter, fakes instead of mocks. Decision taken with the user:
**layered layout, polars**. The requested module names are kept, placed inside layers.

## 4–6. Reuse / change / new

| Requirement | Status | How |
|---|---|---|
| Ollama + LM Studio via OpenAI `/v1` | EXTEND EXISTING / REFACTOR | `backends.py` becomes `adapters/backends.py`; adds `check()` status (never raises) and the streaming call |
| TTFT, total, tokens, tokens/s | REFACTOR | timing logic moves to `application/runner.py` (injectable clock, testable with a fake stream); arithmetic in `domain/metrics.py`; same definitions as before |
| Deterministic tasks + pass/fail | ALREADY IMPLEMENTED | `tasks.py` -> `domain/tasks.py`, unchanged content |
| Result record with extra fields | EXTEND EXISTING | v1 fields kept, new fields added, `schema_version=2` |
| JSONL persistence | EXTEND EXISTING | `adapters/result_store.py`; append per result; reads v1 and v2 rows |
| Cold vs warm | NEW (was only an analysis heuristic) | explicit `cold` flag on the first request per model per benchmark session |
| CSV loading + validation | NEW | `adapters/datasets.py` |
| Hotel statistics | NEW | `adapters/hotel_analysis.py` (polars) -> plain dataclasses in `domain/models.py` |
| Prompt builder | NEW | `application/prompts.py`, versioned |
| JSON response validation | NEW | `application/response_parsing.py` |
| RAM / VRAM monitoring | NEW | `infrastructure/resources.py` (psutil, `nvidia-smi`), sampler thread |
| Orchestration | NEW | `application/benchmark.py` (controller) |
| Marimo notebook | REFACTOR | new `notebooks/llm_hotel_benchmark.py`; old `notebooks/benchmark.py` removed, its deterministic-task benchmark is an option in the new notebook |
| HTTP API | NOT REQUIRED | notebook is the interface; no endpoints, so no versioning question |
| GPU on non-NVIDIA | NOT REQUIRED | reported as unavailable, not emulated |

## 7. Data flow

```
CSV -> datasets.load -> polars frame + DatasetInfo(sha256, rows, dtypes)
    -> hotel_analysis.analyse -> HotelSummary (plain dataclasses)
    -> prompts.build_hotel_prompt -> ChatRequest
    -> benchmark controller -> ChatBackend.stream_chat (+ ResourceMonitor)
    -> runner computes RunMetrics -> response_parsing validates JSON
    -> RunResult -> ResultStore.append (JSONL)
    -> notebook reads the store -> tables / Altair charts / side-by-side responses
```

## 8. Notebook architecture

Composition root for the UI. Holds only widgets, `mo.stop` gating, calls into `nfbench`
and chart definitions. One `mo.state` counter forces reloading results after a run.
Sections 1–12 as specified.

## 9–12. Backends, datasets, prompts, storage

* Backends implement the `ChatBackend` port; both use the same adapter class with different base URLs.
  Unreachable backends yield `BackendStatus(available=False, error=...)`.
* Datasets: explicit `ColumnMapping` (defaults follow the public "Hotel booking demand" schema),
  validation returns errors as data (`DatasetError`), never a crash.
* Prompts get only the deterministic summary, never the CSV.
* Storage: `output/results.jsonl`, one JSON object per line, written immediately per request.

## 13–14. Resource monitoring, errors

Sampler thread while a request runs; RAM = system-wide used memory (the model server is a
separate process), VRAM = `nvidia-smi` summed over GPUs. Missing tooling gives `None`.
Backend failures become `RunResult.error`; the benchmark continues.

## 15–18. Testing, docs, configuration, reproducibility

* pytest with fakes (no servers); integration tests marked and deselected by default.
* `ruff`, `mypy --strict`, `import-linter` configured in `pyproject.toml`.
* `BenchmarkConfig` (temperature, max_tokens, runs, prompt version) stored with every result,
  plus dataset SHA-256, row count and mapping.
* Docs: `README.md`, `ARCHITECTURE.md`, `BENCHMARK_METHODOLOGY.md`, `data/README.md`, `output/README.md`.
