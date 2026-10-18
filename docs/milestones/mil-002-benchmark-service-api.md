# MIL-002 Benchmark service API

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-002 |
| CrossReference | [BC-001], [SA-001], [MIL-001] |
| Language | en |
| Domain | it |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-18 | Proposed | Claude (AI) | S04 | Initial version | [ed03191] |
| 2026-10-18 | Accepted | Claude (AI) | AI at the request of S04, not independent | Accepted after RC-004 Go | pending |

---

## Purpose

Turn the notebook's benchmark into a service that can be started over HTTP and that delivers its result to the web application. The existing layers (`domain`, `application`, `adapters`, `infrastructure`) stay; a presentation layer for the API is added, and the notebook keeps working on the same use cases.

## Deliverable

- An HTTP API on the benchmark service as ADR-0001 says: `POST /runs`, `GET /runs/{id}`, a health endpoint, the service token check, one run at a time.
- A run controller in the application layer that runs the chosen models through the existing benchmark use case and records the state of the run.
- A result sender (adapter) that posts the result to the web API, idempotent on the run id, with the retry rule of ADR-0001 and a store on a volume for results that are not yet delivered.
- The machine description (CPU, memory, GPU or none, backend version) added to the result header.
- Tests with fakes (no network, no Ollama): state transitions, the one-run rule, the 401 and 429 answers, delivery with a fake web API that fails and then recovers.
- Unchanged: the notebook, the result schema version 2, the statistics and the prompts.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | A call without the service token gets 401 on every endpoint except the health endpoint | Yes | No |
| 2 | A run moves `queued`, `running`, `done` or `failed`; a second start during a run is queued or gets 429, as ADR-0001 says | Yes | No |
| 3 | With a fake web API that is down, the result stays on the volume and is delivered once after it returns; a second delivery of the same run id is a no-op | Yes | No |
| 4 | The delivered body validates against the OpenAPI file and carries the machine and the run header | Yes | No |
| 5 | The notebook still runs and its rows have the same fields as before | Yes | No |
| 6 | `ruff`, `mypy --strict` and `import-linter` are clean, all tests pass, and the new tests use fakes only | Yes | No |
| 7 | The code review against `qc-programming-python` has the verdict `Go` | Yes | No |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-001 | The contract and the OpenAPI file the API implements |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| Objectives 3, 4 and 6 | All tasks |
| Success criteria 3, 4, 5, 6, 8 and 9 | Criteria 1 to 6 |

## Ownership

| Role | Stakeholder ID (SA) |
| --- | --- |
| Owner | S01 |
| Approving reviewer | S04 |

## Target Date

2026-11-08 — two weeks after MIL-001: one API, one controller, one sender, with fakes.

## Tasks

| # | Task | Summary | Needs its own Use Case/User Story? | Reference |
| --- | --- | --- | --- | --- |
| 1 | Run controller | State of a run, the queue and the one-run rule in the application layer; unit tests. | No | |
| 2 | HTTP API | `POST /runs`, `GET /runs/{id}`, health, the token check; presentation layer (MVC for an API) and tests. | Yes | UC: administrator starts a benchmark run |
| 3 | Machine description | CPU, memory, GPU or none, and the backend version in the result header. | No | |
| 4 | Result sender and store | Post to the web API, idempotent, retry with growing delay, volume store; tests with a fake web API. | No | |
| 5 | Check and review | Lint, types, import rules, tests; review against `qc-programming-python`. | No | |

---

[BC-001]: ../business-case.md
[SA-001]: ../stakeholder-analysis.md
[MIL-001]: ./mil-001-contract-and-models.md
[ed03191]: https://github.com/NF-Hotel/notebook-benchmark/commit/ed0319185c76fb34b5933731b3889b267c557224
