# RC-025 Review of the list of runs and downloads (MIL-006)

## Metadata
| Key | Value |
| --- | --- |
| ID | RC-025 |
| CrossReference | [MIL-006], [ADR-0006], [QC-PY-001] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Initial version | pending |

---

## Artifact Under Review

- Instance reviewed: the Python source and tests of [MIL-006] on the branch `mil-006-list-runs-and-downloads`: `RunService.list_runs`, `ModelService.list_pulls`, `MAX_LISTED_RUNS` in `domain/service.py`, the two routes and the builder `_model_routes` in `presentation/api.py`, the contract version 1.2.0 and the tests under `tests/`
- Checklist used: [QC-PY-001] (`qc-programming-python`). The checklist file is read from the NFHotel repository's `framework/qc/`, because `framework/qc/` of this repository cannot be initialised.
- Scope: full review of the new and changed code
- Language and domain: n/a for a technical type
- Language reviewer: none
- Mode: autonomous, not independent
- Tool results at the time of review: `ruff check` and `ruff format --check` clean, `mypy --strict` clean (67 files), `lint-imports` 2 contracts kept, `pytest` 286 passed (1 integration test deselected).

## Checklist Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 | PEP 8 casing | Pass | `list_runs`, `list_pulls`, `_model_routes`, `MAX_LISTED_RUNS` |
| 2 | Names state purpose; no unexplained abbreviations | Pass | The names say what they return |
| 3 | Formatter and linter, no unexplained suppressions | Pass | Ruff clean; no new suppression. The model routes were moved out of `create_app` into `_model_routes` because `create_app` passed the 50 statements that the linter allows |
| 4 | Every signature is type-annotated, including `-> None` | Pass | `mypy --strict` clean on 67 files |
| 5 | No bare `except:`, no swallowed exceptions, cause kept | Pass | No new `except` |
| 6 | No mutable default arguments, no shadowed builtins | Pass | The lists return tuples |
| 7 | Files, locks and connections use context managers | Pass | Both lists copy the state under `with self._lock` and release it before building the answer |
| 8 | Public modules, classes and functions have docstrings | Pass | Present on both new methods |
| 9 | `logging` not `print`; no secrets in log output | Pass | Nothing is logged; the token is checked before either list is read |
| 10 | Classes and operations trace to the Design Class Diagram | N-A | This repository has no DCD; the design is ADR-0006 and `ARCHITECTURE.md` |
| 11 | Tests exist, are named for the behaviour, and do not depend on order or the network | Pass | 17 new tests: both lists (empty, newest first, a change of state shown in the next call, the limit of 20), the two routes with the Starlette test client (401, 200, empty array, the fields of the single reads, no clash with `/models/pulls/{id}`), and the contract (status codes, version, the array items and limits equal the code) |
| 12 | Strict type checking; `Any` is justified | Pass | No new `Any` |
| 13 | Dependencies declared and pinned, none unused | Pass | No new dependency |
| 14 | Each piece of knowledge is defined in one place | Pass | The limit of 20 runs is `MAX_LISTED_RUNS`, tested against the contract file like the other limits; the JSON of a run and of a pull is the one function each, used by the single read and by the list |
| 15 | Imports point inward, no cycles | Pass | `lint-imports`: both contracts kept |
| 16 | SOLID | Pass | Two read-only methods on the existing services; no new port |
| 17 | Layers and folders of the clean architecture structure | Pass | The layout recorded in ADR-0003 |
| 18 | File and folder names | Pass | No new source file |

## Overall Verdict

Go — every mandatory criterion passes or is not applicable. The review is not independent. The runs are queued one after the other, so the newest 20 always contain the queued and the running run; if the queue is ever made parallel that argument must be looked at again. The in-memory list of runs is cut only in the answer, not in memory, as ADR-0006 says.

## Action Items

| Action | Owner | Due |
| --- | --- | --- |
| Show the lists on the Start page of NFHotel and check in the VM that a refresh keeps what is running (NFHotel MIL-020) | S01 | With the NFHotel change |

---

[MIL-006]: ../../milestones/mil-006-list-runs-and-downloads.md
[ADR-0006]: ../../adr/adr-0006-list-runs-and-downloads.md
[QC-PY-001]: ../../../framework/qc/code/qc-programming-python.md
