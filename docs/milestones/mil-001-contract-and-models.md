# MIL-001 Contract and models

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-001 |
| CrossReference | [BC-001], [SA-001] |
| Language | en |
| Domain | it |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-18 | Proposed | Claude (AI) | S04 | Initial version | [ed03191] |
| 2026-10-18 | Accepted | Claude (AI) | AI at the request of S04, not independent | Accepted after RC-003 Go | [1f68247] |
| 2026-10-18 | Accepted | Claude (AI) | AI at the request of S04, not independent | Tasks 1 to 4 marked done after RC-007 and RC-008 Go | pending |

---

## Purpose

Decide, before any code, how the benchmark service and the NFHotel web application talk to each other and which models are run. The contract is shared by two repositories, so it is written once, as an Architecture Decision Record (ADR), and both sides build against it. The model list is decided against the memory of the VM, so that a run finishes and its result means something.

## Decisions to record

| # | Decision | Why |
| --- | --- | --- |
| 1 | The web application starts a run: `POST /runs` on the benchmark service with the chosen models and the options of the notebook; the answer is 202 with a run id. `GET /runs/{id}` returns the state (`queued`, `running`, `done`, `failed`) | The administrator starts the run from the back office; the call returns at once because a run takes minutes |
| 2 | One run at a time; a second `POST` while a run is active is queued (up to a small limit) or refused with 429 | The VM is shared; parallel runs would spoil the measurements |
| 3 | When a run ends, the benchmark service sends the result to the web API: `POST /api/benchmark/results`, idempotent on the run id (a repeat changes nothing) | The web application is the only place that stores results; a retry after a failure is harmless |
| 4 | The result body is the result schema version 2 of the notebook (one record per request) plus the run header: run id, start and end time, dataset name and hash, prompt version, the machine (CPU, memory, GPU or none) and the backend version | The notebook and the VM produce the same fields; the machine is named, as the NFHotel Business Case requires |
| 5 | Two service tokens, one per direction, in git-ignored env files: web to benchmark, and benchmark to web (the web API token of ADR-0004 of NFHotel). A call without its token gets 401 | A leak of one token does not open the other direction |
| 6 | If the web API is down, the benchmark service keeps the finished result on a volume and retries with a growing delay for up to 15 minutes, then marks the run `delivery_failed` and keeps the file | The result is never lost, and the state shows what happened |
| 7 | The candidate models are `llama3.2:3b`, `qwen2.5:7b`, `gemma2:9b` and `phi3.5`; the list that is run is sized against the memory of the VM, and at most four are run | A larger list does not fit a CPU-only VM |
| 8 | Models are pulled by a script (`ollama pull`) that checks free disk first and pulls one at a time; a run uses only models that are installed | Reproducible on a new VM, and no download in the middle of a run |

## Deliverable

- ADR-0001 (the contract of decisions 1 to 6) and ADR-0002 (the models of decisions 7 and 8), both reviewed.
- The contract written as an OpenAPI file in this repository, which the NFHotel repository copies or links for its client and its results API.
- The NFHotel milestones that depend on the contract named in the plan (see the NFHotel Project Plan).

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | ADR-0001 states every endpoint, the headers, the status codes, the result body and the retry rule, and the OpenAPI file validates | Yes | No |
| 2 | ADR-0002 names three or four models with their size on disk and the memory needed, and the VM memory they are checked against | Yes | No |
| 3 | The result body of the contract is a superset of schema version 2 in `docs/wiki/Results-Schema.md`; no field is renamed | Yes | No |
| 4 | Both ADRs have a review record with the verdict `Go` | Yes | No |
| 5 | The NFHotel Project Plan lists the milestones that implement the web side of the contract | Yes | No |

## Dependencies

| Depends on | Reason |
| --- | --- |
| BC-001, SA-001 | The objectives and the stakeholders the contract serves |
| ADR-0003 and ADR-0004 of NFHotel | The VM, the network rules and the web API service token |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| Objectives 2, 3, 4 and 6 | Decisions 1 to 8 |
| Success criteria 2, 4, 5, 6 and 8 | Criteria 1 to 3 |

## Ownership

| Role | Stakeholder ID (SA) |
| --- | --- |
| Owner | S01 |
| Approving reviewer | S04; S03 for the models against the VM memory |

## Target Date

2026-10-25 — one week: two ADRs and one contract file.

## Tasks

| # | Task | Summary | Needs its own Use Case/User Story? | Reference |
| --- | --- | --- | --- | --- |
| 1 | Write ADR-0001 | The contract between the web application and the benchmark service, with the options considered (push result, pull result, shared database). | No | Done: ADR-0001, RC-007 |
| 2 | Write the OpenAPI file | `openapi/benchmark-contract.yaml` with the endpoints, schemas and examples; validate it. | No | Done: `openapi/benchmark-contract.yaml` validates |
| 3 | Write ADR-0002 | Model list, sizes, memory check against the VM, and the pull script rules. | No | Done: ADR-0002, RC-008 |
| 4 | Review both ADRs | Against `qc-adr`; record the `RC-*`. | No | Done: RC-007, RC-008 |

---

[BC-001]: ../business-case.md
[SA-001]: ../stakeholder-analysis.md
[ed03191]: https://github.com/NF-Hotel/notebook-benchmark/commit/ed0319185c76fb34b5933731b3889b267c557224
[1f68247]: https://github.com/NF-Hotel/notebook-benchmark/commit/1f68247b4234935b22f03dc9ac66ebfa2eeae72c
