# MIL-004 Prove it in the VM

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-004 |
| CrossReference | [BC-001], [SA-001], [MIL-003] |
| Language | en |
| Domain | it |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-18 | Proposed | Claude (AI) | S04 | Initial version | [ed03191] |
| 2026-10-18 | Accepted | Claude (AI) | AI at the request of S04, not independent | Accepted after RC-006 Go | [1f68247] |

---

## Purpose

Prove the whole chain in the VM: an administrator starts a run in the back office, the benchmark service runs the models in Ollama, the result reaches the web API and is stored, and the administrator reads it again later. This milestone starts when the NFHotel milestones MIL-019 (results API, table, pages) and MIL-020 (start button, client, compose wiring) are accepted, so it is the join of the two repositories.

## Deliverable

- The benchmark and Ollama containers deployed in the VM beside the NFHotel web application and API, with the models of ADR-0002 installed.
- One full run of the chosen models, started from the back office, with the result stored in the web database and read in the admin page.
- A record of the commands and of the numbers of that run in the wiki, with the machine named (CPU only or GPU).
- The resilience check: the web application stopped during a run, started again, and the result delivered.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | A run started in the back office by a Manager reaches `done` and appears in the admin list with every chosen model | Yes | No |
| 2 | The measurements of one model in the admin page equal the values in the result file of the run | Yes | No |
| 3 | With the web application stopped during a run, the result is delivered within 15 minutes after it is started again, and exactly one run row exists | Yes | No |
| 4 | A Receptionist and a Housekeeping user get 403 on the benchmark pages; a call to the benchmark API without the token gets 401 | Yes | No |
| 5 | `docker inspect` shows no published host port for the benchmark and Ollama containers; only ports 80 and 443 of nginx answer from outside | Yes | No |
| 6 | The wiki page names the models, the machine, the times and the commands of the run | Yes | No |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-003 | The containers and the scripts |
| NFHotel MIL-019 and MIL-020 | The results API, the table, the pages, the start button and the compose wiring |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| Objectives 1 to 5 | All tasks |
| Success criteria 3, 5, 6 and 7 | Criteria 1 to 4 |

## Ownership

| Role | Stakeholder ID (SA) |
| --- | --- |
| Owner | S01 |
| Approving reviewer | S04; S03 for the ports and the VM resources |

## Target Date

2027-04-23 — one week after NFHotel MIL-020 (2027-04-16): a deploy and one full run.

## Tasks

| # | Task | Summary | Needs its own Use Case/User Story? | Reference |
| --- | --- | --- | --- | --- |
| 1 | Deploy both sides in the VM | Benchmark and Ollama beside the web application; pull the models. | No | |
| 2 | Run the chain | Start a run in the back office and read it in the admin page; compare with the result file. | No | |
| 3 | Resilience and access checks | Stop and start the web application during a run; the 403, 401 and port checks. | No | |
| 4 | Record the run in the wiki | Models, machine, times, commands. | No | |
| 5 | Review | Against the milestone criteria; record the `RC-*`. | No | |

---

[BC-001]: ../business-case.md
[SA-001]: ../stakeholder-analysis.md
[MIL-003]: ./mil-003-containers-and-deploy.md
[ed03191]: https://github.com/NF-Hotel/notebook-benchmark/commit/ed0319185c76fb34b5933731b3889b267c557224
[1f68247]: https://github.com/NF-Hotel/notebook-benchmark/commit/1f68247b4234935b22f03dc9ac66ebfa2eeae72c
