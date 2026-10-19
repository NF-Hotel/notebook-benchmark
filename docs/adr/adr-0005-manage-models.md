# ADR-0005 The benchmark service pulls and deletes Ollama models

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0005 |
| CrossReference | [BC-001], [MIL-005], [ADR-0001], [ADR-0002], [ADR-0004] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | Proposed | Claude (AI) | S04 | Initial version | [b4a507d] |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Accepted after RC-020 Go | [b4a507d] |

Allowed Status values: `Proposed`, `Accepted`, `Rejected`, `Deprecated`, `Superseded by ADR-NNNN`.

---

## Context

[ADR-0002] fixes a short list of models that `scripts/pull-models.sh` installs. An administrator who wants to try another model, for example `phi4-mini`, or to free the disk of one that is not used, has to log in to the VM. The web application cannot reach Ollama ([ADR-0004]: Ollama is on the network `nfhotel-llm`, which only the benchmark service and the market analysis join), so the calls must be made by the benchmark service, which the web application already calls with a service token ([ADR-0001]).

Forces: a pull is large (gigabytes) and slow (minutes), so the API cannot wait for it; the service must not let a typed name reach anything but a model pull; Ollama is shared with the market analysis, so memory and disk are shared; a run that names a model must not lose it in the middle.

Options considered:

1. **Leave the models to the script.** No change; an administrator needs the command line.
2. **Endpoints on the benchmark service** that call the Ollama API: start a pull (answers at once, runs in the background), read the progress, delete a model.
3. **Expose the Ollama API** to the web application. No code here, but the web application would hold the power to run any Ollama call, and Ollama has no authentication.

## Decision

We follow option 2. The benchmark service gets three routes, all guarded by the service token of [ADR-0001]; `/health` stays open.

- **`POST /models`** with `{"name": "<model>"}` starts a pull and answers 202 with `{pull_id, model, state, percent, error}`. The name must match an Ollama model name: letters, digits, `.`, `_`, `-`, an optional path of up to two `/` parts, and an optional `:tag`, at most 100 characters. Otherwise 400 `invalid_model_name`. A model that is installed is 409 `already_installed`. A pull that is active or queued is 409 `pull_active`: one pull at a time.
- **`GET /models/pulls/{pull_id}`** answers 200 with the same object, or 404 `pull_not_found`. The state is `queued`, `pulling` (with `percent` of the bytes that Ollama reports, or `null` before it reports a total), `done` or `failed` (with `error` set to the reason Ollama gave). The service keeps the last 20 pulls in memory; a restart forgets them.
- **`DELETE /models/{name}`** answers 204 when Ollama deleted the model, 404 `model_not_found` when it is not installed, and 409 `model_in_use` when a queued or running benchmark run names it. The check and the start of a run use the same lock, so a run cannot be queued with the model between the check and the delete.
- **Listing.** `GET /models` is unchanged and lists what Ollama lists, with the tag (`phi4-mini:latest`). A pull of `phi4-mini` is therefore listed as `phi4-mini:latest`; the client takes the name from the list.
- **Disk.** The service cannot see the disk of the Ollama volume, so it does not check free space; Ollama fails a pull that does not fit and the failure is shown as `failed` with its reason. The pull script keeps its own check.
- **Contract.** The OpenAPI file gets a new minor version with the three routes and the new codes; the existing routes do not change.

## Consequences

**Positive:**

- An administrator adds and removes a model from the back office; no login to the VM.
- The web application holds no Ollama power; the only new calls are three narrow ones behind the service token.
- A model that a run needs cannot be deleted under it.

**Negative:**

- Anyone who holds the service token can fill the disk of the VM with pulls (one at a time) or delete a model that no run uses.
- The progress of a pull is kept in memory, so a restart of the service loses it; the pull itself continues in Ollama.
- A pull of a very large model can slow the VM and any run that happens at the same time (shared Ollama, [ADR-0004]).
- The name rule is a syntax check; it does not check that the model exists in the Ollama library, which only the pull learns.

Quality attributes: usability improves (no command line); security is kept (token on every route, a name that cannot carry a path or a command); reliability improves for runs (a model in use is not deleted); performance efficiency is neutral (one pull at a time).

## Affected Artifacts

- [BC-001]
- [MIL-005]
- [ADR-0001]
- [ADR-0002]
- [ADR-0004]

---

[BC-001]: ../business-case.md
[MIL-005]: ../milestones/mil-005-manage-models.md
[ADR-0001]: ./adr-0001-service-contract.md
[ADR-0002]: ./adr-0002-benchmark-models.md
[ADR-0004]: ./adr-0004-use-the-vm-ollama.md
[b4a507d]: https://github.com/NF-Hotel/notebook-benchmark/commit/b4a507d7062e24151cfc8aaa175c15d324dd1317
