# Getting Started

Requires Python 3.11+.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; `source .venv/bin/activate` elsewhere
pip install -e ".[dev]"
```

## Start a model server

| Backend | URL | How |
|---|---|---|
| Ollama | `http://localhost:11434/v1` | `ollama serve` (the desktop app also runs it); `ollama pull <model>` |
| LM Studio | `http://localhost:1234/v1` | Developer tab, start the local server (or `lms server start`) |

You need at least one. If a backend is down the notebook shows it as UNAVAILABLE and keeps working; press **Re-check backends** after starting it.

## Run

```bash
marimo run notebooks/llm_hotel_benchmark.py     # app mode
marimo edit notebooks/llm_hotel_benchmark.py    # editable
```

A synthetic demo CSV is included: `data/example/synthetic_hotel_bookings.csv` (regenerate with `python scripts/make_example_dataset.py`). Its statistics say nothing about real hotels.
