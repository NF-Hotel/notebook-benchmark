# RC-009 Review of the benchmark service API (MIL-002)

## Metadata
| Key | Value |
| --- | --- |
| ID | RC-009 |
| CrossReference | [MIL-002], [ADR-0001], [QC-PY-001] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Initial version | pending |

---

## Artifact Under Review

- Instance reviewed: the Python source and tests of [MIL-002] on the branch `mil-002-benchmark-service-api`: `domain/service.py`, `application/{run_service,delivery,payload,ports}.py`, `adapters/{web_result_sender,pending_store,hotel_input,model_catalog,ollama_info,http_types}.py`, `infrastructure/{machine,worker}.py`, `presentation/api.py`, `bootstrap.py`, and their tests.
- Checklist used: [QC-PY-001] (`qc-programming-python`). The checklist file is read from the NFHotel repository's `framework/qc/` (framework v0.13.2), because `framework/qc/` of this repository cannot be initialised.
- Scope: full review of the new and changed code
- Language and domain: n/a for a technical type
- Language reviewer: none
- Mode: supervised, reviewed by the AI at the request of the user in chat; not independent
- Tool results at the time of review: `ruff check` and `ruff format --check` clean, `mypy --strict` clean (61 files), `lint-imports` 2 contracts kept, `pytest` 178 passed (1 integration test deselected).

## Checklist Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 | PEP 8 casing | Pass | Ruff `N`-style naming not enabled; the code was read: modules `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE` |
| 2 | Names state purpose; no unexplained abbreviations | Pass | `RunService`, `DeliveryService`, `FilePendingStore`; `tick`, `urlopen` and `ok` are established terms |
| 3 | Formatter and linter, no unexplained suppressions | Pass | Ruff clean; the two `# noqa: S310` and `S603` lines carry a reason |
| 4 | Every signature is type-annotated, including `-> None` | Pass | `mypy --strict` clean |
| 5 | No bare `except:`, no swallowed exceptions, cause kept | Pass | `except Exception` in `run_service._run_next` and the worker log the exception and record it; `RunNotFoundError` is raised `from error` (changed during this review from `from None`); `pending_store` logs an unreadable file |
| 6 | No mutable default arguments, no shadowed builtins | Pass | Defaults are immutable or callables |
| 7 | Files, locks and connections use context managers | Pass | `with self._lock`, `with self._urlopen(...) as response`; the thread is joined in `stop()` |
| 8 | Public modules, classes and functions have docstrings | Pass | Present on every public module, class and method |
| 9 | `logging` not `print`; no secrets in log output | Pass | The token is only in the `Authorization` header and never logged; the sender logs the transport error, not the request |
| 10 | Classes and operations trace to the Design Class Diagram | N-A | This repository has no DCD; the design is ADR-0001 and `ARCHITECTURE.md`, which was updated with the new layer and modules |
| 11 | Tests exist, are named for the behaviour, and do not depend on order or the network | Pass | 105 new tests with fakes of every port; the sender, the version reader and the HTTP API are tested with a fake `urlopen` and the Starlette test client; the contract test validates the payload against `openapi/benchmark-contract.yaml` |
| 12 | Strict type checking; `Any` is justified | Pass | `Any` is used only for JSON bodies and `urlopen`, each with a comment |
| 13 | Dependencies declared and pinned, none unused | Pass | `starlette` and `uvicorn` added; `httpx`, `jsonschema`, `pyyaml` and `types-PyYAML` added to `dev`. The project pins lower bounds only (`>=`), as before. `uvicorn` is used by the documented start command, not imported |
| 14 | Each piece of knowledge is defined in one place | Pass | The limits (`MAX_MODELS`, `MAX_RUNS`, `MAX_WAITING_RUNS`, the 15-minute window, the first delay) are in `domain/service.py`; the `UrlOpen` type is in `adapters/http_types.py` (found duplicated in two adapters during this review and merged); the contract is one file |
| 15 | Imports point inward, no cycles | Pass | `lint-imports`: layers contract kept with `presentation` added; the application layer may not import `starlette`, `uvicorn` or `httpx` |
| 16 | SOLID | Pass | One reason to change per class; narrow protocols (`ResultSender`, `PendingResultStore`, `ModelCatalog`, `MachineInspector`); `RunService` depends on ports only |
| 17 | Layers and folders of the clean architecture structure | Fail | The new code follows the layout this repository already has: `adapters` next to `infrastructure`, and `tests/` mirroring `src/` without `unit` and `integration`. The `presentation` package is added as the skill says. The merged layer and the test layout are not recorded in an ADR, which the criterion requires |
| 18 | File and folder names | Pass | English, `snake_case`, no space |

## Overall Verdict

Go-with-conditions — the Mandatory criterion 17 fails, but not because of this change: the layer layout and the test layout were the repository's before MIL-002, and the new code follows them. The condition is an ADR that records them. Every other criterion passes or is not applicable. The review is not independent.

## Action Items

| Action | Owner | Due |
| --- | --- | --- |
| Record in an ADR why `adapters` is kept beside `infrastructure` and why `tests/` mirrors `src/` (or move to `unit` and `integration`) | S01 | Before MIL-003 is closed |
| Run `pytest` with a real Ollama and the web API once, as the integration step of MIL-004 | S01 | MIL-004 |
| Initialise `framework/qc/` of this repository | S01 | Before the next review |
| Write the use case "administrator starts a benchmark run" that task 2 of MIL-002 names (it was not created before the code) | S01 | Before MIL-003 is closed |

---

[MIL-002]: ../../milestones/mil-002-benchmark-service-api.md
[ADR-0001]: ../../adr/adr-0001-service-contract.md
[QC-PY-001]: ../../../framework/qc/code/qc-programming-python.md
