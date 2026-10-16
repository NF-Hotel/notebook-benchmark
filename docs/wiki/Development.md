# Development

```bash
pytest                    # unit tests, no servers needed
pytest -m integration     # needs running Ollama / LM Studio
ruff check . && ruff format --check .
mypy
lint-imports
marimo check notebooks/llm_hotel_benchmark.py
```

- Tests mirror `src/` and use fakes of the ports, not mocks.
- To add another OpenAI-compatible server, add one backend entry in `adapters/backends.py` and `bootstrap.py`.
- For another dataset schema, use a different `ColumnMapping`.
- Dataframes: polars only, confined to adapters.
