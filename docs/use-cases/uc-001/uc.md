# UC-001 Administrator starts a benchmark run

## Metadata
| Key | Value |
| --- | --- |
| ID | UC-001 |
| CrossReference | [US-001], [SA-001], [BC-001], [MIL-002] |
| Language | en |
| Domain | it |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | Proposed | Claude (AI) | S04 | Initial version | [871f21c] |
| 2026-10-19 | Accepted | Claude (AI) | AI at the request of S04, not independent | Accepted after RC-011 Go | [871f21c] |

---

**Format:** Fully Dressed

## Fully Dressed

- **Scope:** The benchmark service together with the NFHotel back office.
- **Level:** user-goal
- **Primary Actor:** Administrator of the back office (S06). The name is the stakeholder name of [SA-001]; no Use Case Diagram exists yet.
- **Stakeholders and Interests:**
  - S06 — starts a run without a command line and finds the result again.
  - S03 — a run stays inside the memory and time of the VM; one run at a time.
  - S02 — every model gets the same prompt, data and settings, and the machine is named.
  - S01 — only the back office can start a run, and its credentials stay out of the repository.
- **Preconditions:**
  - The administrator is signed in and holds the permission to run benchmarks.
  - The benchmark service and the model server are available.
  - At least one model is installed.
- **Postconditions (success guarantee):**
  - A run exists with a run number, in the state queued.
  - When the run has finished, its result is stored once and can be read in the back office.
  - Nothing else was started and no other run was changed.

### Main Success Scenario

1. The administrator asks for the models that can be run.
2. The system lists the installed models.
3. The administrator chooses one to four models and the analysis to make, and starts the run.
4. The system checks the request, queues the run and answers at once with the run number.
5. The administrator follows the state of the run: queued, running, done.
6. The system runs the models one after the other, with the same prompt, data and settings for each, and measures every request.
7. The system delivers the finished result to the web application, which stores it.
8. The administrator sees the run as done with its result stored.

### Extensions / Alternative Flows

- 3a. A chosen model is not installed: the system refuses the request and names the model (US-001.01). Nothing is queued.
- 3b. No model is chosen, more than four are chosen, a model is named twice, or the number of runs is out of range: the system refuses the request and says why.
- 4a. A run is active and two runs are already waiting: the system refuses with a request to try again later. Nothing is queued.
- 4b. The caller cannot prove who it is: the system refuses and starts nothing.
- 6a. A request to a model fails: the system records the error in that request's result and goes on with the next one; the run is still done.
- 6b. The run itself fails (for example the dataset cannot be read): the run ends as failed with the reason, and no result is delivered.
- 7a. The web application does not answer: the system keeps the result and keeps trying for 15 minutes after the run ended; after that the delivery is failed and the result is still kept.
- 7b. The web application refuses the result as invalid or unauthorised: the system does not try again; the delivery is failed at once.

### Special Requirements / Business Rules

- Step 3: one to four models, one to five runs per model, and at least one analysis (hotel cancellation or the deterministic tasks) (ADR-0001, ADR-0002).
- Step 6: one run at a time; one model in memory at a time (ADR-0002).
- Step 7: delivery is idempotent on the run number; the first retry comes after 5 seconds and each wait is twice the one before (ADR-0001).

### Open Issues

- No Use Case Diagram exists; the actor must be renamed if one is made with another name.
- Which analysis options the back office page offers is decided with the NFHotel milestone MIL-020.

---

[US-001]: ../../user-stories.md
[SA-001]: ../../stakeholder-analysis.md
[BC-001]: ../../business-case.md
[MIL-002]: ../../milestones/mil-002-benchmark-service-api.md
[871f21c]: https://github.com/NF-Hotel/notebook-benchmark/commit/871f21c4273b7c045a39fc3e8209d1ade8b4df99
