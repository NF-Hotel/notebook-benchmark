# ADR-0006 The benchmark service lists its runs and its downloads

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0006 |
| CrossReference | [BC-001], [MIL-006], [ADR-0001], [ADR-0005] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | Proposed | Claude (AI) | S04 | Initial version | pending |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Accepted after RC-024 Go | pending |

Allowed Status values: `Proposed`, `Accepted`, `Rejected`, `Deprecated`, `Superseded by ADR-NNNN`.

---

## Context

[ADR-0001] gives the web application one read per run, `GET /runs/{run_id}`, and [ADR-0005] one per download. The web application only learns a run id or a pull id from the answer to the call that started it, and keeps it in the memory of the browser session. After a refresh, or for a second administrator, the page has no id and cannot show what is queued or running, although the service knows.

Options considered:

1. **The web application stores the ids** in its database when it starts a run or a download. No change here, but a run or a download started by any other caller (a second tool, a script with the service token) is still invisible, and the web application would hold a second copy of state that the service owns.
2. **The service lists what it knows**: `GET /runs` and `GET /models/pulls`. The page reads them on load and again every few seconds.
3. **The service pushes changes** (server-sent events or a web socket). Instant, but a long-lived connection through the web application, the proxy and the circuit for a state that changes every few seconds at most.

## Decision

We follow option 2. Two reads are added, both guarded by the service token like every route but `/health`.

- **`GET /runs`** answers 200 with `{"runs": [...]}`, newest first by the time the run was queued, at most 20. Each entry has the fields of `GET /runs/{run_id}`. Queued and running runs are always in the list; the 20 limit cuts the oldest finished runs.
- **`GET /models/pulls`** answers 200 with `{"pulls": [...]}`, newest first. The service already keeps the last 20 downloads; the list is those. Each entry has the fields of `GET /models/pulls/{pull_id}`.
- **Empty is not an error.** With nothing to show, both answer 200 with an empty array.
- **Same memory.** The lists read the state that the single reads read, so a run or a download is in the list in the same moment its own read shows it. A restart of the service forgets them, as before; results that were delivered stay in the web database.
- **Contract.** The OpenAPI file gets a new minor version (1.2.0); the existing routes do not change.
- **Live view.** The web application reads the lists on load and then every 3 seconds while its page is open (NFHotel MIL-020). A change made by any caller shows within that time.

## Consequences

**Positive:**

- The page shows the work in progress after a refresh and for every administrator, whoever started it.
- No state is copied into the web application, and no long-lived connection is needed.

**Negative:**

- A page that is open reads the service every 3 seconds; the reads are cheap (memory only) and are behind the service token.
- A change shows after up to 3 seconds, not at once.
- A restart of the service forgets the queue and the finished runs it listed.
- The list of runs grows in memory with every run (about 1 KB each); it is cut only in the answer, not in memory.

Quality attributes: usability improves (nothing is lost by a refresh); reliability is neutral; security is kept (the token on both routes); performance efficiency is neutral (small in-memory reads at a low rate).

## Affected Artifacts

- [BC-001]
- [MIL-006]
- [ADR-0001]
- [ADR-0005]

---

[BC-001]: ../business-case.md
[MIL-006]: ../milestones/mil-006-list-runs-and-downloads.md
[ADR-0001]: ./adr-0001-service-contract.md
[ADR-0005]: ./adr-0005-manage-models.md
