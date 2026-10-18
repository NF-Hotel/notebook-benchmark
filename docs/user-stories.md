# User Story

## Metadata
| Key | Value |
| --- | --- |
| ID | US-001 |
| CrossReference | [BC-001], [SA-001], [MIL-001], [MIL-002], [MIL-003], [MIL-004] |
| Language | en |
| Domain | it |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | Proposed | Claude (AI) | S04 | Initial version | pending |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Accepted after RC-012 Go (Go with conditions) | pending |

---

## Purpose and Scope

Covers the epics of the benchmark service that an administrator (S06) meets: starting a run of local AI models from the back office and reading its stored result later (objectives 3 to 5 of [BC-001]). The stories are the ones that [MIL-002] task 2 and the NFHotel milestones MIL-019 and MIL-020 implement. No Use Case Diagram exists yet, so the actor name is the stakeholder name of [SA-001].

## Story List

### US-001.01 — Start a benchmark run

**As an** Administrator of the back office (S06), **I want** to choose installed models and start a benchmark run, **so that** I can compare the models without a command line.

**Acceptance Criteria**

- Given models are installed, when I choose one to four of them and start, then I get a run number at once and the run is queued.
- Given a run is active and two are waiting, when I start another, then I am told to try again later and nothing is queued.
- Given I name a model that is not installed, when I start, then I am told which model is missing and nothing is queued.

| Traces to | Size | INVEST exceptions | Priority (MoSCoW) | Reason |
| --- | --- | --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none | Must | Without a start there is no result to read |

### US-001.02 — Read the stored result of a run later

**As an** Administrator of the back office (S06), **I want** to see every finished run and the measurements of each model, **so that** I can choose a model on evidence that is still there tomorrow.

**Acceptance Criteria**

- Given a run has finished and its result was delivered, when I open the list, then I see the run with its models and the machine it ran on.
- Given the web application was down when the run ended, when it is back within 15 minutes, then the run appears once.
- Given I am not an administrator, when I open the list, then I am refused.

| Traces to | Size | INVEST exceptions | Priority (MoSCoW) | Reason |
| --- | --- | --- | --- | --- |
| [MIL-004] (NFHotel MIL-019) | fits one iteration | none | Must | The point of the service is a result that is kept |

## INVEST Check

Both stories are independent (a run can be read without a second one), negotiable in the options a run offers, valuable to S06, estimable, small and testable with the acceptance criteria above. No exception.

---

[BC-001]: ./business-case.md
[SA-001]: ./stakeholder-analysis.md
[MIL-001]: ./milestones/mil-001-contract-and-models.md
[MIL-002]: ./milestones/mil-002-benchmark-service-api.md
[MIL-003]: ./milestones/mil-003-containers-and-deploy.md
[MIL-004]: ./milestones/mil-004-prove-it-in-the-vm.md
[UC-001]: ./use-cases/uc-001/uc.md
