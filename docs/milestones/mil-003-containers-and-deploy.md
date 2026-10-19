# MIL-003 Containers and deploy

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-003 |
| CrossReference | [BC-001], [SA-001], [MIL-002] |
| Language | en |
| Domain | it |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-18 | Proposed | Claude (AI) | S04 | Initial version | [ed03191] |
| 2026-10-18 | Accepted | Claude (AI) | AI at the request of S04, not independent | Accepted after RC-005 Go | [1f68247] |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Tasks 1 to 5 marked done after RC-010 to RC-014 | [871f21c] |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Changed: the compose file starts the benchmark container only, in the project `nfbench`, and uses the Ollama of NFHotel (ADR-0004); criteria 1 and 2 read accordingly. Reviewed in RC-016 and RC-017 | pending |

---

## Purpose

Run the benchmark service and Ollama as containers on the Proxmox VM, beside the NFHotel web application, so that a run can be started with the service token. The whole chain with the web application is proved in MIL-004, after the NFHotel milestones MIL-019 and MIL-020.

## Deliverable

- A Dockerfile for the benchmark service (non-root user, no secrets in the image) and a Compose file with one service, `benchmark`, in the project `nfbench`, on the external networks `nfhotel-llm` and `nfhotel-api`, with no published host port. The Ollama is the one that NFHotel runs on the VM (ADR-0004).
- `benchmark.env.example` (tracked) and the git-ignored `benchmark.env`; the two service tokens are only there.
- A model-pull script that checks free disk and pulls the models of ADR-0002 one at a time into NFHotel's Ollama container.
- A deploy script and a smoke test: the health endpoint answers from the proxy network, a start without a token gets 401, and a short run with one small model reaches `done`, and its result is kept on the volume when no web API answers.
- The wiki pages: how to start the services, pull the models and read a run.
- The same checks run in the VM, with the commands recorded.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | `docker compose up -d` in the VM starts the benchmark container and it is healthy; `docker inspect` shows no published host port | Yes | No |
| 2 | After the pull script `ollama list` in NFHotel's Ollama container shows the models of ADR-0002 and the script exits 0 with no manual input; it refuses to pull when the free disk is below its limit | Yes | No |
| 3 | A run started from the proxy network with the token reaches `done`; with no web API answering, the result stays on the volume and the state shows the delivery as pending | Yes | No |
| 4 | After a restart of the benchmark container the pending result is still on the volume | Yes | No |
| 5 | No token or secret is in git or in the image (`git ls-files` and `docker history` checked) | Yes | No |
| 6 | The code and the shell scripts have `qc-programming-python`, `qc-programming-shell` and `qc-yaml` reviews with the verdict `Go` | Yes | No |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-002 | The API and the sender that are put in the container |
| ADR-0003 of NFHotel | The VM and the network rules |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| Objectives 1, 2 and 3 | All tasks |
| Success criteria 1, 2 and 4 | Criteria 1 to 5 |

## Ownership

| Role | Stakeholder ID (SA) |
| --- | --- |
| Owner | S01 |
| Approving reviewer | S04; S03 for the VM resources and the ports |

## Target Date

2026-11-22 — two weeks after MIL-002: one image, one compose file, one script and a proof in the VM.

## Tasks

| # | Task | Summary | Needs its own Use Case/User Story? | Reference |
| --- | --- | --- | --- | --- |
| 1 | Dockerfile and Compose | The benchmark and Ollama services, network, volumes, health checks, env examples. | No | Done: `Dockerfile`, `deploy/docker-compose.yml`, env examples |
| 2 | Model-pull script | Disk check, one model at a time, exit codes; shell tests. | No | Done: `scripts/pull-models.sh`, `tests/shell/test-pull-models.sh` |
| 3 | Deploy script and smoke test | Start, health, 401 without token, a short run to `done`. | No | Done: `scripts/deploy.sh`, `scripts/smoke-test.sh`; the run to `done` is proved in MIL-004 |
| 4 | Wiki pages | Start, pull, read a run, troubleshooting. | No | Done: `docs/wiki/Service.md` |
| 5 | Check and review | Reviews against `qc-programming-python`, `qc-programming-shell` and `qc-yaml`. | No | Done: RC-010 to RC-014 |

---

[BC-001]: ../business-case.md
[SA-001]: ../stakeholder-analysis.md
[MIL-002]: ./mil-002-benchmark-service-api.md
[ed03191]: https://github.com/NF-Hotel/notebook-benchmark/commit/ed0319185c76fb34b5933731b3889b267c557224
[1f68247]: https://github.com/NF-Hotel/notebook-benchmark/commit/1f68247b4234935b22f03dc9ac66ebfa2eeae72c
[871f21c]: https://github.com/NF-Hotel/notebook-benchmark/commit/871f21c4273b7c045a39fc3e8209d1ade8b4df99
