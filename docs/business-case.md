# Business Case

## Metadata
| Key | Value |
| --- | --- |
| ID | BC-001 |
| CrossReference | [SA-001] |
| Language | en |
| Domain | it |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | Deprecated | Claude (AI) | AI at the request of S04, not independent | Amended: objective 8 (an administrator sees the runs and the model downloads that the service knows, also after a page refresh), one scope item and success criterion 11; accepted after RC-022 Go | [ced9a43] |
| 2026-10-20 | Accepted | Claude (AI) | AI at the request of the user, not independent | Amended: objective 9 (an administrator compares the summaries that the models wrote for the same hotel analysis); accepted by the user in chat on 2026-10-20 after RC-026 Go | [45cab68] |

---

## Executive Summary

The NFHotel 2.0 team wants to choose the local AI model that interprets the hotel's booking statistics, by response time and memory use against answer quality. Today the benchmark is a marimo notebook (`notebooks/llm_hotel_benchmark.py`) that a developer runs by hand on a workstation, and its results stay in `output/results.jsonl` on that machine. This project turns the benchmark into a service: a container on a Proxmox virtual machine (VM), next to an Ollama container and the NFHotel web container, that an administrator starts from the back office. When a run is ready the benchmark service sends the result to the web application's application programming interface (API), which stores it in the web database so that an administrator can view it later. The notebook stays for local work.

## Methodological and Standards Foundation

The work follows the software quality assurance (SQA) and quality control (QC) framework mounted at `framework/` (artifact types, QC checklists, review records) and the plan-first gate of `framework/process/plan-first-gate.md`. Quality is stated with the ISO/IEC 25010 characteristics. The benchmark method itself is that of `BENCHMARK_METHODOLOGY.md`: Python computes the facts, each model only interprets them, and no model is ranked or declared best. The source follows the Clean Architecture of `ARCHITECTURE.md` and the `coding-conventions` skill.

## Problem Statement

- The benchmark runs only by hand on one workstation; nobody else can start it and the result is not where the team looks.
- The result lives in a local file, so it is lost with the machine and cannot be shown in the back office.
- The choice of the local model (US-001.02 and US-001.04 of the NFHotel project) has no repeatable, shared evidence.
- The models must be installed and served on the VM by hand, so a run on a new VM is not reproducible.

## Business Opportunity

If the benchmark runs as a service on the VM, an administrator can start it, wait, and read the same numbers later, for the same models, prompt and data. The team can repeat the run when a model or the VM changes and compare runs over time. The same pattern (a service that reports through an API) can be reused for the market analysis service.

## Objectives

1. Run the benchmark as a container on a Proxmox VM, with the Ollama server in a second container, started by Docker Compose with its own env file and no published host port except through the nginx proxy.
2. Install and serve a small, named set of three to four models in the Ollama container (candidates: `llama3.2:3b`, `qwen2.5:7b`, `gemma2:9b`, `phi3.5`; the final list is decided in an Architecture Decision Record (ADR) against the memory of the VM), pulled by a script and not by hand.
3. Offer an API on the benchmark container with which a run for chosen models is queued and its state is read, and with which nothing else can start a run.
4. When a run is ready, send its result to the web application's API with a service token, so that the web application is the one place that stores results.
5. Store each run and its per-model measurements (time to first token, total time, tokens per second, memory, answer validity) in the web database, and show them to an administrator in the back office for later viewing.
6. Keep the notebook and `output/results.jsonl` working, with the same result schema, so that local and VM runs are comparable.
7. Let an administrator install a further Ollama model, for example `phi4-mini`, and delete an installed one, from the back office through the benchmark service, so the set of models is not fixed by the pull script (the pull and the delete are calls of the service to the Ollama of the VM).
8. Let an administrator see, at any time and from any browser, which runs are queued or running and which model downloads are active, with their state, and let the page follow a change of state without a refresh, so that nothing depends on the browser session that started the work.
9. Let an administrator read the summaries that the models wrote for the same hotel analysis side by side, with the measurements of each answer, so that the choice of the model for the market analysis rests on the quality of the text and not on speed alone.

## Scope

### In Scope

- A Dockerfile and a Compose file for the benchmark service and for Ollama, with env files and tracked `.env.example` files.
- A model-pull script and the list of models (ADR).
- Endpoints on the benchmark service to list the runs and the model downloads that it knows (ADR-0006), and the live view of them in the web application (NFHotel MIL-020).
- Endpoints on the benchmark service to pull a model into Ollama, to read the progress of a pull and to delete an installed model (ADR-0005), and their client and page in the web application (NFHotel MIL-020).
- An HTTP API on the benchmark service (start, status) guarded by a service token, and its client in the web application.
- A results API in the web application, a table in its database and an administrator page that lists runs and shows one run (planned as milestones in the NFHotel repository).
- An ADR for the contract between the two services (endpoints, token, result schema, retries when the web application is down).
- Tests for the service API, the result transfer and the pages; a smoke test in the VM.

### Out of Scope

- A graphical interface on the benchmark service itself; the interface is the back office.
- Ranking the models or choosing one automatically; the administrator reads and decides.
- graphical processing unit (GPU) passthrough to the VM (decided with the VM, ADR-0003 of NFHotel); a run on the central processing unit (CPU) only is valid and is named as such in the result.
- Training or fine-tuning models; hosted AI services.
- LM Studio as a backend of the service (it stays available in the notebook).
- Hosting of the Proxmox server and the creation of the VM.

## Expected Benefits

### Tangible Benefits

- A benchmark run is started and read without a workstation or a command line.
- Results from the VM are kept in the web database, with the machine and the model named, and survive a restart of the VM.
- A run on a new VM needs one compose command and one pull script.

### Intangible Benefits

- A shared, reviewable basis for choosing the local model.
- A pattern for further services that report to the web application.

## Strategic Alignment

The NFHotel Business Case (objective 7) puts the benchmark service on a Proxmox VM behind the proxy, and ADR-0003 of NFHotel decides one KVM VM per service host with Docker Compose inside. This project delivers that service, and its results feed the choice of the AI model for the market analysis service.

## Success Criteria

| # | Criterion | Target | Measure |
| --- | --- | --- | --- |
| 1 | Services up | The benchmark and Ollama containers are running and healthy after `docker compose up -d` in the VM | `docker compose ps` |
| 2 | Models installed | 3 or 4 named models listed by Ollama after the pull script, with 0 manual steps | `ollama list` and the script exit code |
| 3 | Start by an administrator | A run started from the back office is queued and reaches the state `done` or `failed` | Status endpoint and the admin page |
| 4 | Guarded API | A start or status call without the service token gets 401; no host port of the benchmark or Ollama is published | Test and `docker inspect` |
| 5 | Result transfer | The finished run reaches the web API once and is stored; a second delivery of the same run id changes nothing | Contract test and a row count |
| 6 | Resilience | If the web API is down, the result is kept and delivered after it returns, within 15 minutes | Test with a fake web API |
| 7 | Viewing | An administrator sees the list of runs and, for one run, every model with its measurements; other roles get 403 | Page and permission tests |
| 8 | Same schema | A row from the VM and a row from the notebook have the same fields (`schema_version`) | Schema test |
| 9 | Quality gate | 0 build or lint errors, `mypy --strict` clean, all tests pass in both repositories | CI and local run |
| 10 | Models managed by an administrator | A model that is not installed is pulled from the back office and then can be chosen for a run; an installed model is deleted from the back office; a delete of a model that a queued or running run uses is refused | Contract and service tests, and one real pull and delete in the VM |
| 11 | Work that is in progress is visible | After a refresh of the page, or from another browser, the queued and running runs and the active download are listed with their state, and a change of state shows within 5 seconds without a refresh | Service and contract tests, and a check in the VM |
| 12 | Summaries compared | For one session of the hotel analysis with two or more models, the summary of each model is shown side by side with its measurements; an answer that was cut off or not valid says so and shows its raw text | Unit tests of the comparison and the contract test of `GET /runs/{id}/summaries` |

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| The VM has too little memory or no GPU for the larger models | A run is slow or a model does not load; results are not representative | Size the list of models against the memory of the VM in the ADR; name CPU or GPU in every result |
| The web application is down when a run ends | The result is lost | Keep the result on the benchmark side and retry; deliver by run id so a repeat is harmless |
| A run takes long and blocks the VM | The proxy or the web application becomes slow | One run at a time, a queue, a timeout per request, and the run in its own container |
| The service token leaks | Anyone could start runs or post results | Tokens only in git-ignored env files; separate tokens per direction; 401 tests |
| Model downloads are large | The pull fails or fills the disk | The pull script checks free space first and pulls one model at a time |

## Assumptions

- The Proxmox VM, Docker and the compose plugin exist (ADR-0003 of NFHotel) and the NFHotel web container and API run behind the nginx proxy.
- Ollama can be run as a container in the VM and serves an OpenAI-compatible API.
- In supervised mode the user reviews the artifacts of this project.
- The language is English and the domain is IT (as in NFHotel).

## Constraints

- The web application stores the results; the benchmark service holds no database of its own.
- No host port other than 80 and 443 of nginx is published (ADR-0003 and ADR-0006 of NFHotel).
- Secrets stay out of git.
- Nothing is written under `src/` or `tests/` before a milestone is accepted with a Go review (plan-first gate).

## Cost–Benefit Assessment

Qualitative, because no money changes hands: the cost is working time and VM resources, and the benefit is a repeatable choice of the local model.

| Costs | Benefits |
| --- | --- |
| Working time for the service, the contract and the admin page | Shared, repeatable benchmark results |
| VM memory, CPU and disk for the models | No manual installation of models |
| Two more services to deploy and secure | Results kept in the web database for later viewing |

## Stakeholders

| ID | Interest |
| --- | --- |
| S01 | Owns the project and the tokens; wants a benchmark that runs alone and keeps secrets out of git |
| S02 | Uses the result to choose the local model |
| S03 | Guards the memory, CPU, disk and ports of the VM |
| S04 | Reviews and approves the artifacts |
| S05 | Uses the back office that shares the VM; must not be slowed or exposed |
| S06 | Starts runs and reads results in the back office |

## Recommendation

Proceed.

---

[SA-001]: ./stakeholder-analysis.md
[ed03191]: https://github.com/NF-Hotel/notebook-benchmark/commit/ed0319185c76fb34b5933731b3889b267c557224
[b4a507d]: https://github.com/NF-Hotel/notebook-benchmark/commit/b4a507d7062e24151cfc8aaa175c15d324dd1317
[ced9a43]: https://github.com/NF-Hotel/notebook-benchmark/commit/ced9a43ed010056f56f5905fb2b62b399b7e9e42
[45cab68]: https://github.com/NF-Hotel/notebook-benchmark/commit/45cab68a3ddd33cdfd6c26e2ecf3e7d07e419bf2
