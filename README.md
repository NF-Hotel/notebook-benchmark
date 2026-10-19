# Local LLM Hotel Benchmark

A [marimo](https://marimo.io) notebook that benchmarks locally hosted LLMs (Ollama and LM Studio)
on a real-world task: interpreting cancellation statistics of a hotel-booking dataset.
Python computes the facts; each model only interprets them. Speed, memory use and the
answers are then compared side by side. No model is ranked or declared "best".

## What is benchmarked

1. **Hotel cancellation analysis** – the model receives a deterministic statistics summary
   (overall, direct customers vs agent bookings, breakdowns by hotel, market segment, deposit type,
   lead time, ...) and must answer in a fixed JSON structure. The CSV itself is never sent.
2. **Deterministic tasks** (optional) – five short prompts with automatic pass/fail checks.

Measured per request: TTFT, total time, completion tokens, tokens/s, system RAM and GPU VRAM
(before / after / peak), cold vs warm, JSON validity. Details and caveats:
[BENCHMARK_METHODOLOGY.md](BENCHMARK_METHODOLOGY.md).

## Backends

| Backend | URL | Start |
|---|---|---|
| Ollama | `http://localhost:11434/v1` | `ollama serve` (the desktop app also runs it); pull models with `ollama pull <model>` |
| LM Studio | `http://localhost:1234/v1` | LM Studio -> *Developer* tab -> start the local server (or `lms server start`) |

Both are used through their OpenAI-compatible API. The notebook checks each backend, lists its
models, and keeps working if one is down (it is shown as UNAVAILABLE; press *Re-check backends* after starting it).

## Install

Python 3.11+.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; use `source .venv/bin/activate` elsewhere
pip install -e ".[dev]"
```

## Run the notebook

```bash
marimo run notebooks/llm_hotel_benchmark.py      # app mode (code hidden)
marimo edit notebooks/llm_hotel_benchmark.py     # editable
```

In the notebook:

1. **Dataset** – pick a CSV from the dropdown (every `*.csv` below `data/`) or paste any path.
   Column mapping is editable (cancellation column, agent column, categorical columns).
   The file is validated; problems are shown as messages (missing file, invalid or empty CSV,
   missing required columns, unrecognised cancellation values).
2. **Models** – choose one or more models per available backend.
3. **Configuration** – temperature (0), max output tokens (8192), runs per model (1), and whether to
   include the hotel analysis and/or the deterministic tasks.
4. **Run benchmark** – results are appended to `output/results.jsonl` request by request.
5. Read the sections: performance (cold vs warm), Python-calculated cancellation statistics,
   side-by-side model responses next to the calculated values, resources, raw rows, CSV/JSON export.

### Dataset

`data/README.md` lists the expected columns (public "Hotel booking demand" schema). Direct vs agent is
decided by the `agent` column: empty / `NULL` = direct, any other value = agent.
`data/example/synthetic_hotel_bookings.csv` is generated (`python scripts/make_example_dataset.py`) and
is **synthetic**, for trying the pipeline only.

## Results and reproducibility

`output/results.jsonl` holds one JSON object per request (`schema_version` 2) including: timestamp, session id,
backend, model, dataset name / SHA-256 / row count, prompt version, temperature, max tokens, runs,
cold flag, all metrics, RAM/VRAM, finish reason, raw response, validation result and errors.
Every model in a session receives the same prompt and settings. Rows from the first version of the project
(no `schema_version`) are still read.

## Resource measurements

System RAM = system-wide used memory (`psutil`). GPU VRAM = `nvidia-smi` memory in use, summed over GPUs.
Without an NVIDIA GPU / `nvidia-smi`, VRAM is reported as unavailable (null), never as zero. Values include everything
running on the machine, not only the model.

## Project layout

```
notebooks/llm_hotel_benchmark.py   UI only
src/nfbench/domain/                models, metrics, tasks (pure)
src/nfbench/application/           ports, runner, benchmark controller, prompts, response validation
src/nfbench/adapters/              backends (HTTP), datasets + hotel analysis (polars), result store (JSONL)
src/nfbench/infrastructure/        resource monitoring (psutil, nvidia-smi)
src/nfbench/bootstrap.py           composition root
tests/                             mirrors src/
```

See [ARCHITECTURE.md](ARCHITECTURE.md) and [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).
There is no HTTP API; the notebook is the interface.

## Testing and checks

```bash
pytest                      # unit tests; no Ollama / LM Studio needed
pytest -m integration       # optional: needs running servers
ruff check . && ruff format --check .
mypy
lint-imports                # layer contracts
```

## Known limitations

* The cold flag marks the first request per model in a session; if the model was already loaded it is effectively warm.
* Reasoning models can spend the whole token budget thinking; the answer is then reported as invalid (`finish_reason = length`).
  Raise *Max output tokens* if that happens. 1024 was too small for a 2B model's answer to this prompt; the default is 8192 (8K) so that reasoning models have room to think and still write the answer, at the cost of longer runs (the service timeout stays 600 s).
* Valid JSON is a format check; whether the interpretation is correct must be judged by reading the responses.
* Temperature 0 does not guarantee identical outputs across runs or servers.
