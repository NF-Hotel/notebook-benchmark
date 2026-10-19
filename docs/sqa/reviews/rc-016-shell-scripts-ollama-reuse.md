# RC-016 Review of the shell scripts after ADR-0004

## Metadata
| Key | Value |
| --- | --- |
| ID | RC-016 |
| CrossReference | [MIL-003], [ADR-0004], [QC-SH-001] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Initial version | pending |

---

## Artifact Under Review

- Instance reviewed: [MIL-003]: `scripts/lib.sh`, `scripts/deploy.sh`, `scripts/pull-models.sh`, `scripts/smoke-test.sh` (header only), `tests/shell/test-deploy.sh` and `tests/shell/test-pull-models.sh`, changed for [ADR-0004]; this repeats the review of RC-013 for the changed files
- Checklist used: [QC-SH-001]. The checklist file is read from the NFHotel repository's `framework/qc/` (framework v0.13.2), because `framework/qc/` of this repository cannot be initialised.
- Scope: full review
- Language and domain: n/a for a technical type
- Language reviewer: none
- Mode: supervised, reviewed by the AI at the request of the user in chat; not independent

## Checklist Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 | Starts with `#!/usr/bin/env bash` and `set -euo pipefail` (or a comment explains the exception) | Pass | All scripts; the two test scripts use `set -uo pipefail` and say why in their header |
| 2 | Every expansion is quoted; lists are arrays; tests use `[[ ]]` and `$(...)` | Pass | shellcheck clean; `models` is an array |
| 3 | Names follow the conventions | Pass | `kebab-case.sh` files, `snake_case` functions and variables, `UPPER_SNAKE` environment variables (`OLLAMA_CONTAINER`, `OLLAMA_PROJECT`, `OLLAMA_SERVICE`, `BENCHMARK_ENV`) |
| 4 | Passes `shellcheck` and `bash -n` with no unexplained `disable` comments | Pass | shellcheck 0.11.0 with `-x`, `bash -n` on every file, GNU bash 5.2.37; no `disable` comments |
| 5 | Errors go to standard error with an `error:` message and a non-zero exit code; bad arguments print a usage line | Pass | `fail` and explicit `echo ... >&2`; the no-Ollama message says what to do (deploy NFHotel's Ollama or set `OLLAMA_CONTAINER`) |
| 6 | Temporary files use `mktemp` with a `trap ... EXIT` cleanup | Pass | Only the test scripts; `mktemp -d` and a trap |
| 7 | No secret is written in the script, echoed, or put on a command line | Pass | `deploy.sh` reads the tokens from the settings file and prints only their names; `docker exec` carries no secret |
| 8 | A script that changes state outside its own directory defaults to a dry run or needs an explicit flag, and says so in its header | Pass | Same interpretation as RC-013: `deploy.sh` and `pull-models.sh` exist only to change state and say so; `pull-models.sh` now changes the volume of NFHotel's Ollama, which its header names |
| 9 | A header comment states purpose, usage, options, environment variables and exit codes | Pass | All scripts, updated for the new variables |
| 10 | The script implements a task or design it cites; deviations are recorded | Pass | Headers cite MIL-003, ADR-0002 and ADR-0004; the deviation from MIL-003 (one container) is recorded in ADR-0004 |
| 11 | Behaviour is tested for success, failure and any disabled or bypass path | Pass | 22 checks for the pull script (labels, named container, other project and service, no container, Docker down, too little disk, failed pull) and 19 for the deploy script (both networks checked, either missing, tokens, missing file, unhealthy, unknown option). The checks were written first and failed against the old scripts. The smoke test run to `done` is not exercised here (MIL-004) |
| 12 | Formatted with `shfmt` | N-A | `shfmt` is not installed; optional |
| 13 | Safe to re-run | Pass | Installed models are skipped; `compose up` updates what changed |
| 14 | Bash version and external tools it needs are stated | Pass | Each header has a Needs line |
| 15 | A command sequence, constant, path or message used more than once is defined once | Pass | `compose`, `fail`, the paths and the one settings file are in `lib.sh`; the `OLLAMA_ENV` variable that duplicated the settings file is gone |

## Overall Verdict

Go — every mandatory criterion passes. The scripts were run only against a fake `docker`; a real Docker host and the VM are the work of MIL-004. The review is not independent.

## Action Items

| Action | Owner | Due |
| --- | --- | --- |
| Run `scripts/deploy.sh`, `scripts/pull-models.sh` and `scripts/smoke-test.sh` on the VM | S01 | MIL-004 |

---

[MIL-003]: ../../milestones/mil-003-containers-and-deploy.md
[ADR-0004]: ../../adr/adr-0004-use-the-vm-ollama.md
[QC-SH-001]: ../../../framework/qc/code/qc-programming-shell.md
