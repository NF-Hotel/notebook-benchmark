# RC-014 Review of deploy/docker-compose.yml

## Metadata
| Key | Value |
| --- | --- |
| ID | RC-014 |
| CrossReference | [MIL-003], [QC-YML-001] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Initial version | pending |

---

## Artifact Under Review

- Instance reviewed: [MIL-003]: `deploy/docker-compose.yml` (the Dockerfile and the `.env.example` files have no checklist and were read, not scored)
- Checklist used: [QC-YML-001]. The checklist file is read from the NFHotel repository's `framework/qc/` (framework v0.13.2), because `framework/qc/` of this repository cannot be initialised.
- Scope: full review
- Language and domain: n/a for a technical type
- Language reviewer: none
- Mode: supervised, reviewed by the AI at the request of the user in chat; not independent

## Checklist Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 | The file parses with a safe YAML loader and has no duplicate keys | Pass | PyYAML 6.0.3 `SafeLoader` with a duplicate-key check; `docker compose config -q` accepts it |
| 2 | Indentation is 2 spaces, LF line ends, one final newline, no trailing spaces | Pass | Checked by yamllint |
| 3 | Passes `yamllint` with its configuration committed next to the code | Pass | yamllint 1.38.0 with `.yamllint.yml`, also clean on the existing workflow file |
| 4 | A scalar that YAML would coerce is quoted | Pass | Ports are quoted strings; no `yes`, `no` or version-like scalar |
| 5 | Only safe, plain types are used | Pass | No tags |
| 6 | No secret is written in the file | Pass | Tokens are in the git-ignored env files; the example files hold `change-me` |
| 7 | Embedded program text in a value is at most five lines | Pass | None |
| 8 | A block of keys or values repeated is defined once | Pass | No repeated block |
| 9 | Anchors, aliases and merge keys are used only where the tool supports them | Pass | None used |
| 10 | The file validates against the schema of the consuming tool | Pass | `docker compose config -q` (Docker Compose v2, Docker 29.8.2) with the env files of the examples |
| 11 | A header comment states what the file is for, which tool reads it, and where its decision is recorded | Pass | Docker Compose; ADR-0001 and ADR-0002 |
| 12 | Key names follow the convention of the consuming tool | Pass | Compose keys |
| 13 | Multi-line strings use a block scalar | Pass | None |
| 14 | The file name is lowercase kebab-case with one extension style | Pass | `docker-compose.yml`, like `.github/workflows/publish-wiki.yml` |
| 15 | A change is exercised by a check that runs without the real target | Pass | `docker compose config -q`; the built image ran read-only as a non-root user; the `ollama` container itself was not started |

## Overall Verdict

Go — every mandatory criterion passes. The compose file was validated, not started with Ollama; that is MIL-004. The review is not independent.

## Action Items

| Action | Owner | Due |
| --- | --- | --- |
| Start the compose file in the VM and run the smoke test | S01 | MIL-004 |

---

[MIL-003]: ../../milestones/mil-003-containers-and-deploy.md
[QC-YML-001]: ../../../framework/qc/code/qc-yaml.md
