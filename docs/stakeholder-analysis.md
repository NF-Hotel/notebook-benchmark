# Stakeholder Analysis

## Metadata
| Key | Value |
| --- | --- |
| ID | SA-001 |
| CrossReference | [BC-001] |
| Language | en |
| Domain | it |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-18 | Accepted | Claude (AI) | AI at the request of S04, not independent | Initial version | pending |

---

## Purpose

Identifies who influences or is affected by the benchmark service and the way it reports to the NFHotel web application, so that owners, reviewers and RACI entries elsewhere can cite stable IDs. The IDs S01 to S05 are those of the NFHotel Stakeholder Analysis and keep their meaning; S06 is new. The method is a power/interest grid; concerns are mapped to FURPS+.

## Stakeholder Summary Table

| ID | Name | Role/Title | Organization | Power Level | Interest Level | Quadrant | Primary Concern (Business Language) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | Team 2 | Owner of NF Hotel and of this project; its members are all developers; owner of the credentials and the tokens | NFHotel 2.0 project | HIGH | HIGH | Manage Closely | A benchmark that runs alone, repeatably, and never leaks a token |
| S02 | Other NFHotel 2.0 guilds | Developers of the DevOps, frontend, mobile and cybersecurity tracks; they use the result to choose the local model | NFHotel 2.0 project | MEDIUM | HIGH | Keep Informed | Trustworthy numbers for the model choice, and a service that does not disturb the shared VM |
| S03 | Proxmox VE administrator | Owner of the Proxmox server and the VM | NFHotel 2.0 project (held by S01 for now) | HIGH | MEDIUM | Keep Satisfied | The runs stay inside the memory, CPU and disk of the VM and open no new host port |
| S04 | Valdamar | Stand-in for the Product Owner; reviewer and approver of the artifacts | NFHotel 2.0 project | HIGH | HIGH | Manage Closely | A clear plan and a result he can accept or reject |
| S05 | Hotel staff | Receptionists and housekeeping who use the back office; represented by S01 and S04 until real users are named | NF Hotel | LOW | LOW | Monitor | That the benchmark never slows or exposes the back office they use |
| S06 | Administrator of the back office | The Manager who starts a benchmark run from the back office and reads the results later | NF Hotel | MEDIUM | HIGH | Keep Informed | Start a run without a command line and find the result again, with the machine and the model named |

## Power/Interest Classification Rationale

- S01 owns the project, builds both services and holds the tokens: high power, high interest.
- S02 uses the result but cannot block it: medium power, high interest.
- S03 can refuse VM resources or stop the containers at any time: high power; interest is medium because the service is one more container on the VM.
- S04 (Valdamar) stands in for the Product Owner: he reviews and accepts every artifact, so high power and high interest. S01 and S03 are the same group today (Team 2); the roles stay separate so the Business Case can name who guards the server.
- S05 does not decide the project and does not use the benchmark: low power, low interest. They are listed because the benchmark runs next to the back office on the same VM; S01 and S04 speak for them.
- S06 is the one who starts runs and reads results: medium power (the result drives the model choice), high interest. The Manager role of the NFHotel permission table is the administrator; S01 and S04 speak for S06 until a real administrator is named.

## Primary Concerns and FURPS+ Mapping

| ID | Concern | FURPS+ attribute |
| --- | --- | --- |
| S01 | Run without interaction; tokens stay out of git | Usability, Functionality (security) |
| S02 | Same prompt, data and settings for every model; the machine is named in the result | Functionality, Reliability |
| S03 | Bounded memory and time per run; one run at a time; no published host port | Performance, Reliability |
| S04 | Reviewable, traceable artifacts | Maintainability |
| S05 | The back office stays fast and private while a run is in progress | Performance, Functionality (security) |
| S06 | Start a run and read its result later in the back office | Usability, Functionality |

## Communication Requirements

| ID | Channel | Frequency | Deliverable | Phase / Milestone |
| --- | --- | --- | --- | --- |
| S01 | Chat | Per milestone | Run summary with review records | MIL-001 |
| S02 | Repository README and wiki | On change | How to start a run and how to read the numbers | MIL-001 |
| S03 | Chat | Once per VM | Memory, CPU and disk the containers need; the ports that stay closed | MIL-003 |
| S04 | Chat | Per milestone | Review records and run summary | MIL-001 |
| S05 | Through S01 and S04 | On change | Note when a run is scheduled on the shared VM | MIL-004 |
| S06 | The back office page | On each run | The list of runs and the result of one run | NFHotel MIL-019 |

## Conflicting Interests and Mitigations

| Conflict | Stakeholders | Mitigation |
| --- | --- | --- |
| Larger models give better answers versus the memory of the shared VM | S02, S03 | The ADR sizes the list of models against the VM; every result names the machine; one run at a time |
| Easy start from the back office versus a run that blocks the VM | S06, S03 | One queued run at a time, a timeout per request, and a clear state in the page |
| Sharing results versus keeping tokens secret | S02, S01 | Results are read in the back office; tokens live only in git-ignored env files |

## Traceability Analysis

### Business Goal Alignment

| Stakeholder | Concern | Business Case objective |
| --- | --- | --- |
| S01 | Run without interaction; tokens stay out of git | Objectives 1, 3 and 4 |
| S02 | Same schema and named machine | Objectives 5 and 6 |
| S03 | Bounded resources, no published host port | Objectives 1 and 3 |
| S04 | Reviewable, traceable artifacts | Objectives 1 to 6 |
| S05 | The back office stays fast and private | Objectives 1 and 3 |
| S06 | Start a run and read it later | Objectives 3 and 5 |

## Sign-Off

Reviewer and approver: S04. In supervised mode the user reviews and the AI does not stand in for S04.

---

[BC-001]: ./business-case.md
