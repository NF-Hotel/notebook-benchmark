# MIL-006 List runs and downloads

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-006 |
| CrossReference | [BC-001], [SA-001], [MIL-005], [ADR-0006] |
| Language | en |
| Domain | it |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | Proposed | Claude (AI) | S04 | Initial version | [ced9a43] |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Accepted after RC-023 Go | [ced9a43] |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Tasks 1 to 5 marked done after RC-024 and RC-025 | pending |

---

## Purpose

After a refresh of the page, or from another browser, an administrator could no longer see which run was queued or running, or which model download was active, because the web application only knew the run id of the run that its own session started. The service knows them all; it only has no way to list them. This milestone adds two reads, so that the page can show what is in progress at any time and follow a change of state.

## Deliverable

- ADR-0006 and a new version of `openapi/benchmark-contract.yaml` with `GET /runs` and `GET /models/pulls`.
- A list of the runs that the run service knows, newest first, and a list of the downloads that the model service knows, newest first.
- The two routes in the API, guarded by the service token.
- Tests with fakes and a contract test.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | `GET /runs` answers 200 with the queued, running and recent finished runs, newest first, at most 20, each with the fields of `GET /runs/{run_id}` | Yes | No |
| 2 | `GET /models/pulls` answers 200 with the downloads that the service keeps, newest first, each with the fields of `GET /models/pulls/{pull_id}` | Yes | No |
| 3 | With no run and no download, both answer 200 with an empty list | Yes | No |
| 4 | A run that changes state (queued, running, done) is shown in the next call, and a download that moves from queued to done likewise | Yes | No |
| 5 | Both routes answer 401 without the service token | Yes | No |
| 6 | The contract file validates and a test compares the status codes and the fields of the routes with the code | Yes | No |
| 7 | `mypy --strict`, the linter and all tests pass; the review against `qc-programming-python` has the verdict `Go` | Yes | No |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-005 | The model service and its downloads |
| ADR-0006 | The contract and the limits |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| Objective 8, success criterion 11 | All tasks |
| Objective 3 (guarded API) | Criterion 5 |

## Ownership

| Role | Stakeholder ID (SA) |
| --- | --- |
| Owner | S01 |
| Approving reviewer | S04 |

## Target Date

2026-10-26 — one week.

## Tasks

| # | Task | Summary | Needs its own Use Case/User Story? | Reference |
| --- | --- | --- | --- | --- |
| 1 | Record the decision | ADR-0006 and the new version of the OpenAPI file; reviews. | No | Done: ADR-0006, OpenAPI 1.2.0, RC-024 |
| 2 | Lists in the services | The newest 20 runs and the kept downloads, newest first. | No | Done: `RunService.list_runs`, `ModelService.list_pulls` |
| 3 | Routes | `GET /runs` and `GET /models/pulls` with the token check. | No | Done: `GET /runs`, `GET /models/pulls` |
| 4 | Tests | Service, API and contract tests with fakes. | No | Done: 17 new tests, 286 in all |
| 5 | Review | Against the milestone criteria and `qc-programming-python`; record the `RC-*`. | No | Done: RC-025 |

---

[BC-001]: ../business-case.md
[SA-001]: ../stakeholder-analysis.md
[MIL-005]: ./mil-005-manage-models.md
[ADR-0006]: ../adr/adr-0006-list-runs-and-downloads.md
[ced9a43]: https://github.com/NF-Hotel/notebook-benchmark/commit/ced9a43ed010056f56f5905fb2b62b399b7e9e42
