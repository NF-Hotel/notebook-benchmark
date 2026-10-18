# ADR-0001 The contract between the web application and the benchmark service

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0001 |
| CrossReference | [BC-001], [MIL-001] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-18 | Proposed | Claude (AI) | S04 | Initial version | pending |
| 2026-10-18 | Accepted | Claude (AI) | AI at the request of S04, not independent | Accepted after RC-007 Go | pending |

Allowed Status values: `Proposed`, `Accepted`, `Rejected`, `Deprecated`, `Superseded by ADR-NNNN`.

---

## Context

An administrator starts a benchmark run in the back office of the NFHotel web application. The run is made by the benchmark service, in its own container on the same VM, against models in an Ollama container. A run takes minutes (several models, cold and warm requests), so a call cannot wait for it. The result must end up in the web database, because the web application is the one place that stores results and shows them to an administrator (objectives 4 and 5 of [BC-001]).

Forces: the VM is shared and small, so one run at a time; the web application must not be blocked or lose a result when it restarts; the benchmark service holds no database; both services are on an internal Docker network and publish no host port; a leak of one token must not open the other direction; the notebook and the VM must produce the same result fields.

Options considered for how the result gets to the web application:

1. **The benchmark service pushes the finished result** to the web API, with a retry. The web API is idempotent on the run id.
2. **The web application polls** the benchmark service for the state and fetches the result when it is done. The benchmark service then keeps the result until it is fetched, and the web application needs a background poller.
3. **A shared database or volume.** The benchmark service writes straight into PostgreSQL or a shared file. This puts the database login in a second service and breaks the rule of ADR-0004 of NFHotel that only the API reaches the database.

## Decision

We follow option 1. The contract is the OpenAPI file `openapi/benchmark-contract.yaml`; this record gives the reasons and the rules the file cannot state.

- **Start.** The web application calls `POST /runs` on the benchmark service with the chosen models and options. The answer is 202 with a run id and the state `queued`. `GET /runs/{run_id}` returns the state (`queued`, `running`, `done`, `failed`) and the state of the delivery (`not_ready`, `pending`, `delivered`, `failed`). `GET /models` lists the installed models so that the start page offers only models that exist. `GET /health` needs no token.
- **One run at a time.** A run that is started while another is active is queued, up to two waiting runs; a third gets 429 with `Retry-After`. Models inside a run are run one after the other.
- **Delivery.** When a run is `done`, the benchmark service writes the whole result to a file on its volume and then posts it to `POST /api/benchmark/results` of the web API. The web API answers 201 for a new run id and 200 for a repeat, and stores nothing twice. A body that does not match the contract, or has a `schema_version` other than 2, gets 400 and stores nothing.
- **Retry.** If the post fails (no answer, a 5xx), the service retries after 5 seconds and doubles the delay each time, up to 15 minutes after the run ended. After that the delivery is `failed` and the file stays on the volume. A 400 or 401 is not retried: it is a defect, and the delivery is `failed` at once with the reason in the log. The unsent results are tried again when the service starts.
- **Result body.** The run header (run id, start and end, prompt version, dataset name, hash and rows, the machine with CPU, memory and GPU or none, the backend and its version) and one record per request in the result schema version 2 of the notebook. No field of the notebook is renamed, so a row from the VM and a row from the notebook compare directly.
- **Tokens.** Each call carries `Authorization: Bearer <token>`. The web application holds the token of the benchmark service; the benchmark service holds the service token of the web API (ADR-0004 of NFHotel). The two are different secrets in the git-ignored env files. A missing or wrong token gets 401. The staff token is not used between the services: the web application checks that the user is a Manager before it calls the benchmark service, and the web API checks the same before it shows a run.
- **Network.** Both services are on the internal Docker network; neither publishes a host port, and nginx has no route to the benchmark service.

## Consequences

**Positive:**

- The web application is the one place that stores and shows results, and the benchmark service holds no database.
- A result is never lost: it is on the volume until the web API has it, and a repeat delivery is harmless.
- The start returns at once, so the back office stays responsive during a run.
- The contract is a file that both repositories can test against.

**Negative:**

- The benchmark service needs a small queue, a store for unsent results and a retry loop that must be tested with a fake web API.
- The web application must show a run that is `done` but not yet delivered as such; the page cannot assume that a finished run is stored.
- A change of the contract touches two repositories and needs a new ADR and a new version of the file.
- The service token of the web API is held by one more service, so a leak of the benchmark container exposes it.

Quality attributes: reliability improves (no result is lost, repeats are harmless); security is kept (separate tokens per direction, no published port); maintainability improves (one contract file tested on both sides); performance is neutral (the start returns at once, a run is one at a time).

## Affected Artifacts

- [BC-001]
- [MIL-001]

---

[BC-001]: ../business-case.md
[MIL-001]: ../milestones/mil-001-contract-and-models.md
