# MIL-005 Manage models

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-005 |
| CrossReference | [BC-001], [SA-001], [MIL-002], [ADR-0005] |
| Language | en |
| Domain | it |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | Proposed | Claude (AI) | S04 | Initial version | [b4a507d] |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Accepted after RC-019 Go | [b4a507d] |

---

## Purpose

Let an administrator install a further Ollama model, for example `phi4-mini`, and delete an installed one, without a command line. The web application cannot reach Ollama, so the benchmark service, which can, gets three calls: start a pull, read its progress, and delete a model. The page that uses them is built in the NFHotel repository (MIL-020).

## Deliverable

- ADR-0005 and a new version of `openapi/benchmark-contract.yaml` with `POST /models`, `GET /models/pulls/{pull_id}` and `DELETE /models/{name}`.
- A port and an Ollama adapter that pulls a model with progress and deletes a model.
- A model service that checks the name, runs one pull at a time in the background, keeps the progress of the pulls and refuses to delete a model that a queued or running run uses.
- The three routes in the API, guarded by the service token, with the status codes of the contract.
- Tests with a fake Ollama: no test needs the network or a model.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | `POST /models` with a valid name answers 202 with a pull id; the progress goes from `queued` to `pulling` with a percentage to `done`, and the model is then listed by `GET /models` | Yes | No |
| 2 | A name that is not an Ollama model name, a model that is installed, and a second pull while one is active are refused with 400, 409 and 409 and a code each | Yes | No |
| 3 | A pull that Ollama fails ends in `failed` with the reason and leaves no model listed | Yes | No |
| 4 | `DELETE /models/{name}` answers 204 and the model is no longer listed; an unknown model is 404; a model that a queued or running run names is 409 and stays installed | Yes | No |
| 5 | Every new route answers 401 without the service token, and `/health` stays open | Yes | No |
| 6 | The OpenAPI file validates and a test compares the status codes of the routes with it | Yes | No |
| 7 | `mypy --strict`, the linter and all tests pass; the review against `qc-programming-python` has the verdict `Go` | Yes | No |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-002 | The API, the run service and the queue that the delete must look at |
| ADR-0005 | The contract and the safety rules |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| Objective 7, success criterion 10 | All tasks |
| Objective 3 (guarded API) | Criterion 5 |

## Ownership

| Role | Stakeholder ID (SA) |
| --- | --- |
| Owner | S01 |
| Approving reviewer | S04; S03 for the disk that a pull uses |

## Target Date

2026-10-26 — one week.

## Tasks

| # | Task | Summary | Needs its own Use Case/User Story? | Reference |
| --- | --- | --- | --- | --- |
| 1 | Record the decision | ADR-0005 and the new version of the OpenAPI file; reviews. | No | |
| 2 | Ollama adapter and model service | Pull with progress, delete, name check, one pull at a time, delete refused for a model in use. | No | |
| 3 | Routes and wiring | The three routes, the token check, the status codes; composition root. | No | |
| 4 | Tests | Service and API tests with fakes, and the contract status codes. | No | |
| 5 | Review | Against the milestone criteria and `qc-programming-python`; record the `RC-*`. | No | |

---

[BC-001]: ../business-case.md
[SA-001]: ../stakeholder-analysis.md
[MIL-002]: ./mil-002-benchmark-service-api.md
[ADR-0005]: ../adr/adr-0005-manage-models.md
[b4a507d]: https://github.com/NF-Hotel/notebook-benchmark/commit/b4a507d7062e24151cfc8aaa175c15d324dd1317
