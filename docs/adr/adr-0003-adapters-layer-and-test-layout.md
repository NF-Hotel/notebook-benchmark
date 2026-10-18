# ADR-0003 The adapters layer and the layout of the tests

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0003 |
| CrossReference | [BC-001], [MIL-003], [RC-009] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | Proposed | Claude (AI) | S04 | Initial version | pending |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Accepted after RC-010 Go | pending |

Allowed Status values: `Proposed`, `Accepted`, `Rejected`, `Deprecated`, `Superseded by ADR-NNNN`.

---

## Context

Criterion 17 of `qc-programming-python` asks for the layers `domain`, `application`, `infrastructure` and `presentation` under `src/`, and `unit`, `integration` and `e2e` under `tests/`, and accepts a merged layer when an ADR says why. The review RC-009 of MIL-002 found that this repository has two packages where the skill has one, `adapters` and `infrastructure`, and that `tests/` mirrors `src/` instead of being split by kind of test. Both existed before MIL-002 (`docs/IMPLEMENTATION_PLAN.md` took the layered layout in 2026-09-27); the new code follows them.

What is in the two packages:

- `adapters`: code that speaks to an external system through a port of the application layer: the OpenAI-compatible HTTP client, the CSV reader, the JSONL store, the sender to the web API, the file store of unsent results.
- `infrastructure`: code that reads or controls the machine and the process: memory and GPU sampling, the machine description, the background thread.

Options considered:

1. **Merge both into `infrastructure`.** Matches the skill. About 14 modules in one package, and a rename of every import of `nfbench.adapters` in the code, the tests and the notebook.
2. **Keep both packages and record why.** No churn; the import-linter contract already treats them as siblings of one layer.
3. **Rename `adapters` to `infrastructure` and fold the other one into a subpackage.** The same churn as option 1 with a nested name.

For the tests: all tests of this repository run without a network or a model server (fakes of the ports); the few that need a running Ollama or LM Studio carry the marker `integration` and are deselected by default. There are no end-to-end tests yet.

## Decision

We follow option 2: `adapters` and `infrastructure` are siblings in the infrastructure layer of the skill, checked by one import-linter contract (`presentation | adapters | infrastructure`), and the tests stay mirrored on `src/` with the marker `integration` for tests that need a real server. A `tests/integration/` and a `tests/e2e/` folder are made when the first such test is written.

## Consequences

**Positive:**

- No rename of imports and no churn in the notebook or in earlier reviews.
- The dependency rule is unchanged and still checked by `lint-imports`.
- The difference between talking to an external system and reading the machine stays visible in the package names.

**Negative:**

- The layout differs from the skill's wording, so a reader who knows the skill has to read this record.
- A new module needs a decision (adapter or infrastructure); the rule above (a port to an external system is an adapter) must be applied by hand.
- Unit and integration tests are not separated by folder; only the marker tells them apart.

Quality attributes: maintainability is neutral (the same dependency rule, one more package name to know); portability is unchanged (the application layer imports no framework).

## Affected Artifacts

- [BC-001]
- [MIL-003]
- [RC-009]

---

[BC-001]: ../business-case.md
[MIL-003]: ../milestones/mil-003-containers-and-deploy.md
[RC-009]: ../sqa/reviews/rc-009-benchmark-service-api-code.md
