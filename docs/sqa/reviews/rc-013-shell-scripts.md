# RC-013 Review of the shell scripts of MIL-003

## Metadata
| Key | Value |
| --- | --- |
| ID | RC-013 |
| CrossReference | [MIL-003], [QC-SH-001] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Initial version | pending |

---

## Artifact Under Review

- Instance reviewed: [MIL-003]: `scripts/lib.sh`, `scripts/deploy.sh`, `scripts/pull-models.sh`, `scripts/smoke-test.sh`, `tests/shell/test-deploy.sh`, `tests/shell/test-pull-models.sh`
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
| 3 | Names follow the conventions | Pass | `deploy.sh`, `pull-models.sh`, `smoke-test.sh`, `test-deploy.sh`; `snake_case` variables and functions |
| 4 | Passes `shellcheck` and `bash -n` with no unexplained `disable` comments | Pass | shellcheck 0.11.0 with `-x`, `bash -n` on every file, GNU bash 5.2.37; no `disable` comments |
| 5 | Errors go to standard error with an `error:` message and a non-zero exit code; bad arguments print a usage line | Pass | `fail` and the explicit `echo ... >&2`; `smoke-test.sh --bogus` prints the usage (tested) |
| 6 | Temporary files use `mktemp` with a `trap ... EXIT` cleanup | Pass | Only the test scripts need a temporary folder; they use `mktemp -d` and a trap |
| 7 | No secret is written in the script, echoed, or put on a command line | Pass | `deploy.sh` reads the tokens from the env file and never prints them; the smoke test reads the token inside the container |
| 8 | A script that changes state outside its own directory defaults to a dry run or needs an explicit flag, and says so in its header | Pass | Interpretation: `deploy.sh` and `pull-models.sh` exist only to change state and say so in the header; running them is the explicit act. The smoke test says it starts a real run. No dry run exists |
| 9 | A header comment states purpose, usage, options, environment variables and exit codes | Pass | All scripts |
| 10 | The script implements a task or design it cites; deviations are recorded | Pass | Each header cites MIL-003; the pull script cites ADR-0002 |
| 11 | Behaviour is tested for success, failure and any disabled or bypass path | Pass | 26 checks with a fake `docker` for `deploy.sh` and `pull-models.sh` (success, missing settings, `change-me` tokens, missing network, unhealthy, too little disk, Ollama down, failed pull). The probe of `smoke-test.sh` was run by hand against the built container (health 200, 401 without a token, exit 3 with no model); the run to `done` and `--restart-check` have not been run and are the work of MIL-004 |
| 12 | Formatted with `shfmt` | N-A | `shfmt` is not installed here; optional |
| 13 | Safe to re-run | Pass | `deploy.sh` and `pull-models.sh` are idempotent (installed models are skipped) |
| 14 | Bash version and external tools it needs are stated | Pass | Each header has a Needs line |
| 15 | A command sequence, constant, path or message used more than once is defined once | Pass | `compose`, `fail` and the paths are in `scripts/lib.sh` (found duplicated during this review and merged) |

## Overall Verdict

Go — every mandatory criterion passes. The part of the smoke test that needs Ollama and a model is not yet exercised; it is proved in MIL-004. The review is not independent.

## Action Items

| Action | Owner | Due |
| --- | --- | --- |
| Run `scripts/smoke-test.sh` and `--restart-check` against a VM with Ollama and a model | S01 | MIL-004 |

---

[MIL-003]: ../../milestones/mil-003-containers-and-deploy.md
[QC-SH-001]: ../../../framework/qc/code/qc-programming-shell.md
