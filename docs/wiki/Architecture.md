# Architecture

Clean Architecture; dependencies point inward, enforced by `import-linter`. Details: `ARCHITECTURE.md` in the repo.

```mermaid
flowchart TD
    NB[Marimo notebook] --> BOOT[bootstrap.py]
    BOOT --> CTRL[Benchmark controller]
    CTRL --> RUN[LLM runner] --> BACK[Backend adapter]
    BACK --> OLL[Ollama]
    BACK --> LMS[LM Studio]
    CTRL --> PROMPT[Prompt builder]
    CTRL --> PARSE[Response validation]
    CTRL --> RES[Resource monitor]
    CTRL --> STORE[Result store JSONL]
    NB --> DS[Dataset loader] --> AN[Hotel analysis] --> PROMPT
    RUN --> MET[Metrics]
```

| Layer | Modules |
|---|---|
| `domain` | models, metrics, tasks, errors (pure) |
| `application` | ports, runner, benchmark controller, prompts, response parsing |
| `adapters` | backends (HTTP), datasets, hotel analysis (polars), result store |
| `infrastructure` | resource monitoring (psutil, nvidia-smi) |
| `bootstrap.py` | composition root |

The notebook holds UI only. There is no HTTP API.
