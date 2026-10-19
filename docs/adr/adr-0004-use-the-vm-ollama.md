# ADR-0004 The benchmark service uses the Ollama of the VM

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0004 |
| CrossReference | [BC-001], [MIL-003], [MIL-004], [ADR-0002] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | Proposed | Claude (AI) | S04 | Initial version | pending |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Accepted after RC-015 Go | pending |

Allowed Status values: `Proposed`, `Accepted`, `Rejected`, `Deprecated`, `Superseded by ADR-NNNN`.

---

## Context

MIL-003 gave the benchmark service its own Ollama container in its own compose file. While the proof in the VM was planned (MIL-004, `docs/wiki/Prove-it-in-the-VM.md`), two facts of the VM were checked against it:

- The VM already runs an Ollama for the market analysis (`deploy/ollama` of NFHotel, compose project and service `ollama`, network `nfhotel-llm`, a volume of models). The VM has 12 GiB memory and 60 GiB disk (NFHotel ADR-0003 and ADR-0004). A second Ollama would add a second server in memory and a second copy of every model on disk (about 15 GB for the four models of ADR-0002).
- NFHotel's old benchmark notebook (`deploy/benchmark`) uses the compose project name `benchmark`, a service `benchmark` and a volume `results`, exactly as the new compose file did. Starting the new file would have replaced the old container and reused its volume.

Options considered:

1. **Keep the second Ollama** and only rename the project. No change to NFHotel; double memory and disk, and two places where models are installed.
2. **Use the Ollama of the VM**: the benchmark container joins `nfhotel-llm`, reaches `http://ollama:11434`, and the pull script pulls into that container. One model server and one set of models; the market analysis and the benchmark share it.
3. **Stop the market analysis during a run.** Safe for memory but a manual rule that nobody will remember.

## Decision

We follow option 2, and rename the compose project to `nfbench`. The compose file starts only the benchmark container, on the networks `nfhotel-llm` and `nfhotel-api` (both made by NFHotel); `scripts/pull-models.sh` finds the Ollama container by its compose labels (`OLLAMA_CONTAINER`, `OLLAMA_PROJECT` and `OLLAMA_SERVICE` override), and `OLLAMA_MAX_LOADED_MODELS=1` and `OLLAMA_NUM_PARALLEL=1` of ADR-0002 are set in the `ollama.env` of NFHotel.

## Consequences

**Positive:**

- One model server and one copy of each model on the 12 GiB VM; the pull script's disk check applies to the volume that is really used.
- The old notebook service and its volume are left alone.
- The benchmark service no longer needs the internet itself; only the shared Ollama does.

**Negative:**

- A benchmark run and a market analysis that run at the same moment share one model at a time, so both slow down and the measured times include the other load; runs must not overlap.
- The benchmark service now depends on NFHotel's deploy: it cannot start before the network `nfhotel-llm` and the Ollama container exist.
- The settings that ADR-0002 needs (`OLLAMA_MAX_LOADED_MODELS`, `OLLAMA_NUM_PARALLEL`) live in another repository and its example file does not have them yet.
- MIL-003 and the Business Case describe "Ollama in a second container" beside the service; the container is now NFHotel's. Their text is not changed here and needs a new version when this ADR is accepted.

Quality attributes: performance efficiency improves (memory and disk are not doubled); maintainability is neutral (one fewer service here, one more cross-repository dependency); security is kept (no new port, the benchmark container keeps its read-only root and no capabilities).

## Affected Artifacts

- [BC-001]
- [MIL-003]
- [MIL-004]
- [ADR-0002]

---

[BC-001]: ../business-case.md
[MIL-003]: ../milestones/mil-003-containers-and-deploy.md
[MIL-004]: ../milestones/mil-004-prove-it-in-the-vm.md
[ADR-0002]: ./adr-0002-benchmark-models.md
