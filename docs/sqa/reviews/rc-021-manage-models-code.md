# RC-021 Review of the model management code (MIL-005)

## Metadata
| Key | Value |
| --- | --- |
| ID | RC-021 |
| CrossReference | [MIL-005], [ADR-0005], [QC-PY-001] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Initial version | pending |

---

## Artifact Under Review

- Instance reviewed: the Python source and tests of [MIL-005] on the branch `mil-005-manage-models`: `application/model_service.py`, `adapters/ollama_models.py`, the new ports and types in `application/ports.py` and `domain/{service,errors}.py`, `RunService.delete_if_unused`, the three routes in `presentation/api.py`, the wiring in `bootstrap.py`, the contract version 1.1.0 and the tests under `tests/`
- Checklist used: [QC-PY-001] (`qc-programming-python`). The checklist file is read from the NFHotel repository's `framework/qc/`, because `framework/qc/` of this repository cannot be initialised.
- Scope: full review of the new and changed code
- Language and domain: n/a for a technical type
- Language reviewer: none
- Mode: autonomous, not independent
- Tool results at the time of review: `ruff check` and `ruff format --check` clean, `mypy --strict` clean (67 files), `lint-imports` 2 contracts kept, `pytest` 269 passed (1 integration test deselected).

## Checklist Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 | PEP 8 casing | Pass | New modules `model_service.py` and `ollama_models.py` are `snake_case`; classes `ModelService`, `OllamaModelAdmin`, `PullStatus`; constants `UPPER_SNAKE` |
| 2 | Names state purpose; no unexplained abbreviations | Pass | `start_pull`, `pull_status`, `delete_if_unused`, `ModelUseGuard`; `urlopen` is an established term |
| 3 | Formatter and linter, no unexplained suppressions | Pass | Ruff clean; two `# type: ignore[arg-type]` are on `dataclasses.replace` with computed field names (as in `RunService._set`) and on the test of a request body, each short and local |
| 4 | Every signature is type-annotated, including `-> None` | Pass | `mypy --strict` clean on 67 files |
| 5 | No bare `except:`, no swallowed exceptions, cause kept | Pass | `ModelService._run_pull` catches `BackendError` and, for a defect, `Exception`, logs it and ends the pull as `failed`, so a pull cannot stay `pulling` for ever; the adapter raises `BackendError ... from error` |
| 6 | No mutable default arguments, no shadowed builtins | Pass | Defaults are immutable or callables |
| 7 | Files, locks and connections use context managers | Pass | `with self._lock`, `with self._urlopen(...) as response`; the pull thread is a daemon thread that ends with the process |
| 8 | Public modules, classes and functions have docstrings | Pass | Present on every new public module, class and method |
| 9 | `logging` not `print`; no secrets in log output | Pass | A failed pull logs the model and the reason, never the token; the token stays in the `Authorization` header of the API |
| 10 | Classes and operations trace to the Design Class Diagram | N-A | This repository has no DCD; the design is ADR-0005 and `ARCHITECTURE.md`, which was updated |
| 11 | Tests exist, are named for the behaviour, and do not depend on order or the network | Pass | 91 new tests with fakes: the model service (name rules, one pull at a time, the last 20 pulls, failures, delete and its refusals), the Ollama adapter with a fake `urlopen`, the API with the Starlette test client, the guard in `RunService`, and the contract file (status codes, states and name pattern equal the code) |
| 12 | Strict type checking; `Any` is justified | Pass | `Any` only for JSON bodies with a comment, as before |
| 13 | Dependencies declared and pinned, none unused | Pass | No new dependency: `urllib` and the existing `starlette` |
| 14 | Each piece of knowledge is defined in one place | Pass | The name pattern, the limit of kept pulls and the states are in `domain/service.py`; a test shows that the OpenAPI file equals them; `RunService._require_installed` is the one check of installed models for a run |
| 15 | Imports point inward, no cycles | Pass | `lint-imports`: both contracts kept; the application layer imports no `starlette` or `urllib` |
| 16 | SOLID | Pass | `ModelService` depends on three narrow ports (`ModelCatalog`, `ModelAdmin`, `ModelUseGuard`); `RunService` implements the guard; the adapter has one reason to change |
| 17 | Layers and folders of the clean architecture structure | Pass | The new code follows the layout recorded in ADR-0003 (`adapters`, `application`, `presentation`, `tests/` mirroring `src/`) |
| 18 | File and folder names | Pass | English, `snake_case`, no space |

## Overall Verdict

Go — every mandatory criterion passes or is not applicable. The review is not independent. Two decisions are open to challenge: the service does not check free disk (it cannot see the Ollama volume; Ollama fails a pull that does not fit and the reason is shown), and a run is now checked against the installed models under the lock that the delete takes, which moved that check after the queue-full check.

## Action Items

| Action | Owner | Due |
| --- | --- | --- |
| Do one real pull and delete in the VM through the NFHotel page (NFHotel MIL-020) | S01 | With the NFHotel change |

---

[MIL-005]: ../../milestones/mil-005-manage-models.md
[ADR-0005]: ../../adr/adr-0005-manage-models.md
[QC-PY-001]: ../../../framework/qc/code/qc-programming-python.md
