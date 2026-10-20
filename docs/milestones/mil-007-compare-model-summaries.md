# MIL-007 Compare the summaries of the models

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-007 |
| CrossReference | [BC-001], [SA-001], [MIL-006], [US-001] |
| Language | en |
| Domain | it |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-20 | Accepted | Claude (AI) | AI at the request of the user, not independent | Initial version; accepted by the user in chat on 2026-10-20 after RC-028 Go | [45cab68] |

---

## Purpose

Let an administrator read the summaries that the models wrote for the same hotel analysis side by side. Today the benchmark measures speed, memory and whether the answer was valid JSON, but the text of the `summary` field stays in the raw results, so a model that is fast and valid but writes a poor summary looks as good as one that writes a good one. The choice of the default model of the market analysis (NFHotel ADR-0014) rests on that text. The milestone adds a comparison of the summaries to the notebook and a read of it in the service API; the page in the web application is a later milestone of NFHotel. It delivers [US-001] story US-001.03 and objective 9 of [BC-001].

## Deliverable

- A comparison of the summaries in the application layer: for one session of the hotel analysis, one entry per model and repetition with the `summary` text, the characters, the completion tokens, the finish reason, whether the answer was valid, the tokens per second and, for an answer that was cut off or not valid, its raw text and the reason.
- A section "Compare the summaries" in the notebook: the models side by side for the same prompt, a choice of the session and of the repetition, and a clear mark on an entry that was cut off or invalid.
- A read in the service API and in `openapi/benchmark-contract.yaml`: `GET /runs/{id}/summaries`, guarded by the service token, with a contract test.
- Tests with fakes, and the wiki page and the README updated.
- Out of scope: a scored judge model, the page in the web application, a change of the prompt or of the result schema.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | For a result file with three models and one session, the comparison has one entry per model with the `summary` of the stored answer, and a test compares each entry with the stored `output` | Yes | No |
| 2 | An answer cut off at the maximum output tokens (`finish_reason` `length`) or not valid JSON has no summary; its entry says why and carries the raw text | Yes | No |
| 3 | With several repetitions the comparison reads the repetition that is asked for, and the first one by default | Yes | No |
| 4 | A session with no hotel analysis gives an empty comparison with a message and no error | Yes | No |
| 5 | The notebook section shows the models side by side and starts without error on the sample results file of the tests | Yes | No |
| 6 | `GET /runs/{id}/summaries` returns the same entries, answers 404 for an unknown run and 401 without the service token; the contract file describes it and a test fails when they differ | Yes | No |
| 7 | The result schema, the stored files and the existing routes are unchanged (the existing tests pass without edits) | Yes | No |
| 8 | Tests pass, the linters are clean, and the `qc-programming-python` and `qc-yaml` reviews have the verdict `Go` | Yes | No |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-006 | The list of runs and the stored results that the comparison reads |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| Objective 9 of BC-001 | All tasks |
| US-001.03 Compare the summaries of the models | Tasks 1 to 3 |

## Ownership

| Role | Stakeholder ID (SA) |
| --- | --- |
| Owner | S01 |
| Approving reviewer | S04 |

## Target Date

2026-11-06 — about two weeks from the plan, so that the model for the market analysis (NFHotel MIL-027) can be chosen on summaries; for S01 to confirm.

## Tasks

| # | Task | Summary | Needs its own Use Case/User Story? | Reference |
| --- | --- | --- | --- | --- |
| 1 | Comparison of the summaries | Build the comparison in the application layer from the stored results of a session: one entry per model and repetition with the summary text, characters, completion tokens, finish reason, validity, tokens per second and, for a cut off or invalid answer, the raw text and reason; reuse `response_parsing`. Unit tests with fake results. | Yes | US-001.03. Done: `SummaryEntry` and `SummaryComparison` (domain), `compare_summaries` (application), 11 tests; on the 135 stored results it shows a cut off answer of `phi4-reasoning:plus` and two empty answers |
| 2 | Notebook section | Add "Compare the summaries" to `notebooks/llm_hotel_benchmark.py`: choose the session and the repetition, show the models side by side with the measurements, and mark a cut off or invalid answer. | Yes | US-001.03. Done: section 10 of the notebook (the later sections are renumbered 11 to 13); the notebook exports headless on the stored results without an error; not looked at in a browser |
| 3 | Service read | `GET /runs/{id}/summaries` in the service API with the service token, the route in `openapi/benchmark-contract.yaml`, and a contract test; 404 for an unknown run. | Yes | US-001.03. Done: `RunService.summaries`, `FilePendingStore.find`, route and contract version 1.3.0, 409 for a run with no result and 400 for a bad `run`; the repetition is numbered as in the result, from 0; the test that pinned contract version 1.2.0 was changed to 1.3.0 |
| 4 | Documents | Update the README, the wiki page of the notebook and the results schema page, and describe the new route. | No | Done: wiki pages Using-the-Notebook and Service (the results schema is unchanged) |
| 5 | Check and review | Tests, linters and the reviews against `qc-programming-python` and `qc-yaml`; record the RC. | No | |

---

[BC-001]: ../business-case.md
[SA-001]: ../stakeholder-analysis.md
[MIL-006]: ./mil-006-list-runs-and-downloads.md
[US-001]: ../user-stories.md
[45cab68]: https://github.com/NF-Hotel/notebook-benchmark/commit/45cab68a3ddd33cdfd6c26e2ecf3e7d07e419bf2
