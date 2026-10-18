# ADR-0002 The models of the benchmark service

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0002 |
| CrossReference | [BC-001], [MIL-001], [ADR-0001] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-18 | Proposed | Claude (AI) | S04 | Initial version | pending |
| 2026-10-18 | Accepted | Claude (AI) | AI at the request of S04, not independent | Accepted after RC-008 Go | pending |

Allowed Status values: `Proposed`, `Accepted`, `Rejected`, `Deprecated`, `Superseded by ADR-NNNN`.

---

## Context

The benchmark service runs a small, named set of models in an Ollama container on the Proxmox VM and compares them by response time, memory use and answer quality. NFHotel ADR-0003 and ADR-0004 describe one VM of about 12 GiB memory and 60 GiB disk that also runs nginx, the web application, the API and PostgreSQL. Whether the VM has a GPU is not known, so a run on the CPU only is assumed. Ollama downloads a model once and keeps it on disk; a model that is used is loaded into memory and needs about its file size plus room for the context.

Candidate models, with the approximate download size of the default 4-bit build in the Ollama library (to be checked at pull time with `ollama list`):

| Model | Parameters | Size on disk | Memory while loaded (estimate) |
| --- | --- | --- | --- |
| `llama3.2:3b` | 3 billion | about 2.0 GB | about 3 GB |
| `phi3.5` | 3.8 billion | about 2.2 GB | about 3.5 GB |
| `qwen2.5:7b` | 7 billion | about 4.7 GB | about 6.5 GB |
| `gemma2:9b` | 9 billion | about 5.4 GB | about 8 GB |

Options considered:

1. **All four models always.** About 14 GB of disk, but `gemma2:9b` needs about 8 GB of the 12 GiB, which leaves too little for the web application, the API and PostgreSQL while a run is active.
2. **Three models by default, the fourth when the VM is larger.** The three smaller models fit; `gemma2:9b` is added when the VM has at least 16 GiB memory.
3. **Only the smallest model.** Safe, but it gives nothing to compare.

## Decision

We follow option 2. The default list is `llama3.2:3b`, `phi3.5` and `qwen2.5:7b`; `gemma2:9b` is installed and run only when the VM has at least 16 GiB memory, which S03 confirms.

- **One model in memory.** Ollama runs with `OLLAMA_MAX_LOADED_MODELS=1` and `OLLAMA_NUM_PARALLEL=1`, so a second model is loaded only after the first is unloaded.
- **Pull script.** A script pulls the models one at a time with `ollama pull`. It first reads the free disk and stops with a non-zero exit code when less than 20 GB is free. It is safe to run again: a model that is installed is skipped.
- **Only installed models.** A run is accepted only for models that `GET /models` lists; an unknown or not installed model gets 400 ([ADR-0001]).
- **The machine is named.** Every result names the CPU, the memory and the GPU or none ([ADR-0001]), so a CPU-only run is not mistaken for a GPU run.
- **No ranking.** The list is for comparison; the service never picks a model by itself (BENCHMARK_METHODOLOGY.md).
- **Changing the list.** A change of the default list is a new version of this record, not a code change; the service reads the allowed names from its configuration.

## Consequences

**Positive:**

- A run fits in the memory of the shared VM and does not starve the web application.
- A new VM is set up with one compose command and one script.
- The comparison covers two sizes of small model and one mid-size model.

**Negative:**

- On a CPU only the 7-billion model is slow, so a full run takes a long time; the runs per model stay at 1 by default.
- The sizes above are estimates and may change with a new build of a model; the pull script logs the real size.
- `gemma2:9b` is missing from the default comparison until the VM is larger.
- Memory figures include everything that runs on the VM, as BENCHMARK_METHODOLOGY.md says, so they are upper bounds for the model alone.

Quality attributes: performance efficiency is protected (one model in memory, runs one at a time); portability improves (the same script and compose file on any VM); reliability improves (a memory limit instead of a swapped-out VM).

## Affected Artifacts

- [BC-001]
- [MIL-001]
- [ADR-0001]

---

[BC-001]: ../business-case.md
[MIL-001]: ../milestones/mil-001-contract-and-models.md
[ADR-0001]: ./adr-0001-service-contract.md
