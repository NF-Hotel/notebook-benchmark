# RC-017 Review of deploy/docker-compose.yml after ADR-0004

## Metadata
| Key | Value |
| --- | --- |
| ID | RC-017 |
| CrossReference | [MIL-003], [ADR-0004], [QC-YML-001] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Initial version | pending |

---

## Artifact Under Review

- Instance reviewed: [MIL-003]: `deploy/docker-compose.yml`, changed for [ADR-0004] (project `nfbench`, one service, two external networks); this repeats the review of RC-014
- Checklist used: [QC-YML-001]. The checklist file is read from the NFHotel repository's `framework/qc/` (framework v0.13.2), because `framework/qc/` of this repository cannot be initialised.
- Scope: full review
- Language and domain: n/a for a technical type
- Language reviewer: none
- Mode: supervised, reviewed by the AI at the request of the user in chat; not independent

## Checklist Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 | The file parses with a safe YAML loader and has no duplicate keys | Pass | `docker compose config -q` accepts it (Docker Compose v2, Docker 29.8.2) with the example settings file |
| 2 | Indentation is 2 spaces, LF line ends, one final newline, no trailing spaces | Pass | yamllint 1.38.0 clean |
| 3 | Passes `yamllint` with its configuration committed next to the code | Pass | `.yamllint.yml` of the repository |
| 4 | A scalar that YAML would coerce is quoted | Pass | The port is a quoted string; `name: nfbench` is not a coerced scalar |
| 5 | Only safe, plain types are used | Pass | No tags |
| 6 | No secret is written in the file | Pass | Tokens are only in the git-ignored settings file |
| 7 | Embedded program text in a value is at most five lines | Pass | None |
| 8 | A block of keys or values repeated is defined once | Pass | None |
| 9 | Anchors, aliases and merge keys are used only where the tool supports them | Pass | None |
| 10 | The file validates against the schema of the consuming tool | Pass | `docker compose config -q` |
| 11 | A header comment states what the file is for, which tool reads it, and where its decision is recorded | Pass | Docker Compose; ADR-0001 and ADR-0004; the comment explains the two networks and the project name |
| 12 | Key names follow the convention of the consuming tool | Pass | Compose keys |
| 13 | Multi-line strings use a block scalar | Pass | None |
| 14 | The file name is lowercase kebab-case with one extension style | Pass | `docker-compose.yml` |
| 15 | A change is exercised by a check that runs without the real target | Pass | `docker compose config -q`. The container was not started here; the external networks must exist for `up` and `deploy.sh` checks them |

## Overall Verdict

Go — every mandatory criterion passes. The file starts one container; the Ollama it uses is NFHotel's. The review is not independent.

## Action Items

| Action | Owner | Due |
| --- | --- | --- |
| Start the file in the VM beside NFHotel and check that the old notebook service is untouched | S01 | MIL-004 |

---

[MIL-003]: ../../milestones/mil-003-containers-and-deploy.md
[ADR-0004]: ../../adr/adr-0004-use-the-vm-ollama.md
[QC-YML-001]: ../../../framework/qc/code/qc-yaml.md
