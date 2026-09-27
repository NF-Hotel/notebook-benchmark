The repo's .claude rules (python-developer agent) require Clean Architecture layers (domain/application/adapters/infrastructure), polars-first, ruff + mypy --strict + import-linter. Your spec asks for flat modules (datasets.py, analysis.py, ...). Which structure should I use?

Layered per repo rules (Recommended)

Dataframe library for dataset loading/analysis? (Repo rules prefer polars; the current notebook uses pandas and Altair accepts both.)

polars (Recommended)
