# Project: Marimo LLM Benchmark – Hotel Booking Analysis

You are an experienced Python software architect and developer.

We are extending an **existing local LLM benchmark project** into a Marimo-based benchmark for evaluating local LLMs on a real-world hotel-booking dataset.

The project already contains working benchmark code. **Do not rewrite the project from scratch. First inspect the existing implementation and extend it while preserving working functionality.**

The current project already supports Ollama and LM Studio through their OpenAI-compatible `/v1` APIs. The existing implementation also measures TTFT, total execution time, completion tokens, tokens/sec and optional task pass/fail results.

Existing files include:

* `src/nfbench/backends.py`
* `src/nfbench/runner.py`
* `src/nfbench/tasks.py`
* `src/nfbench/benchmark.py`
* `src/nfbench/__init__.py`

The existing backend implementation uses:

* Ollama: `http://localhost:11434/v1`
* LM Studio: `http://localhost:1234/v1`

The existing runner already streams completions and records:

* `ttft_s`
* `total_s`
* `completion_tokens`
* `tokens_per_s`
* `passed`
* model
* backend
* task
* output
* error

Do not remove this functionality.

---

# 1. Development Process

Follow this process strictly:

## Phase 1 – Planning

Before writing or modifying code, analyse the existing project.

Create a detailed implementation plan covering:

1. Current architecture
2. Existing modules and responsibilities
3. Existing benchmark functionality
4. What can be reused
5. What needs to change
6. New components required
7. Data flow
8. Marimo notebook architecture
9. Backend architecture
10. Dataset handling
11. LLM prompt execution
12. Result storage
13. Resource monitoring
14. Error handling
15. Testing strategy
16. Documentation
17. Configuration
18. Reproducibility

Do not start coding until the plan is complete.

---

# 2. Project Structure

The target structure should be approximately:

```text
.
├── README.md
├── ARCHITECTURE.md
├── pyproject.toml
├── .gitignore
│
├── notebooks/
│   └── llm_hotel_benchmark.py
│
├── src/
│   └── nfbench/
│       ├── __init__.py
│       ├── backends.py
│       ├── runner.py
│       ├── tasks.py
│       ├── benchmark.py
│       ├── datasets.py
│       ├── metrics.py
│       ├── resources.py
│       ├── analysis.py
│       └── models.py
│
├── tests/
│   ├── test_backends.py
│   ├── test_runner.py
│   ├── test_datasets.py
│   ├── test_metrics.py
│   └── test_analysis.py
│
├── data/
│   └── README.md
│
└── output/
    └── README.md
```

The notebook **must be kept in `./notebooks`**.

Python application/backend code **must be kept in `./src/`**.

Do not put business logic directly into the Marimo notebook when it belongs in `src/`.

The notebook should primarily provide:

* user interface
* configuration
* execution control
* visualisation
* result presentation

---

# 3. Required Artifacts Before Coding

Before implementing the code, create/update these artifacts.

## README.md

Document:

* Project purpose
* What is being benchmarked
* Ollama support
* LM Studio support
* Dataset requirements
* How to install dependencies
* How to start Ollama
* How to start LM Studio
* How to run the Marimo notebook
* How to select models
* How to select a CSV dataset
* Benchmark methodology
* Metrics
* Resource measurements
* Result files
* Reproducibility
* Testing

---

## ARCHITECTURE.md

Document the architecture.

Include a Mermaid or PlantUML architecture diagram.

Describe at least:

```text
Marimo Notebook
       |
       v
Benchmark Controller
       |
       +---- Backend Adapter
       |        |
       |        +---- Ollama
       |        |
       |        +---- LM Studio
       |
       +---- Dataset Loader
       |
       +---- Prompt Builder
       |
       +---- LLM Runner
       |
       +---- Metrics Collector
       |
       +---- Resource Monitor
       |
       +---- Result Store
       |
       +---- Analysis
```

Clearly define the responsibility of each component.

---

## Benchmark Methodology Document

Create a document explaining how the benchmark works.

Document:

* What is measured
* How measurements are taken
* Cold vs warm execution
* TTFT
* Total execution time
* Completion tokens
* Tokens/sec
* Task pass/fail
* GPU VRAM
* System RAM
* Dataset size
* Number of repetitions
* Temperature
* Maximum output tokens
* How results should be interpreted

Avoid making claims that cannot be measured.

---

# 4. Existing Benchmark Must Be Preserved

The current benchmark functionality must remain available.

The existing runner already calculates TTFT and tokens/sec from streamed responses.

Preserve the existing behavior where possible rather than duplicating it.

The existing result structure includes:

```text
backend
model
task_id
category
run
ttft_s
total_s
completion_tokens
tokens_per_s
passed
output
error
```

Extend this structure rather than replacing it.

Add fields where necessary, for example:

```text
dataset
dataset_rows
analysis_type
system_ram_before
system_ram_after
system_ram_peak
gpu_vram_before
gpu_vram_after
gpu_vram_peak
prompt_tokens
timestamp
duration
```

Only add fields that can actually be measured reliably.

---

# 5. Local LLM Backends

Support:

## Ollama

```text
http://localhost:11434/v1
```

## LM Studio

```text
http://localhost:1234/v1
```

Both expose an OpenAI-compatible API.

Keep the backend abstraction.

The user should not need to know implementation-specific API details.

The notebook should detect which backends are available.

For each available backend:

1. Check connectivity
2. Retrieve available models
3. Show models in the UI
4. Allow the user to select one or more models

If a backend is unavailable, the notebook must continue working and clearly show that backend as unavailable.

Do not crash the entire benchmark because one backend is unavailable.

---

# 6. Marimo Notebook

Create the main notebook:

```text
./notebooks/llm_hotel_benchmark.py
```

The notebook must be implemented using Marimo.

The notebook should have clear sections.

Recommended structure:

```text
# Local LLM Hotel Benchmark

1. Environment / Backend Status
2. Dataset Selection
3. Model Selection
4. Benchmark Configuration
5. Dataset Overview
6. Benchmark Execution
7. Performance Results
8. Hotel Cancellation Analysis
9. LLM Analysis Comparison
10. Resource Usage
11. Raw Results
12. Export
```

---

# 7. Dataset Selection

The user must be able to select the CSV file **inside the notebook**.

The dataset selection must be in the same configuration area where the user selects the LLM/backend.

Do not hard-code a single CSV filename.

The UI should allow the user to select a CSV file from an appropriate local directory.

After selecting the CSV:

1. Load it
2. Validate it
3. Display the filename
4. Display number of rows
5. Display number of columns
6. Display column names
7. Display a sample
8. Display basic data types
9. Display missing-value information

The implementation must handle:

* missing file
* invalid CSV
* empty CSV
* missing required columns
* malformed data

with useful error messages.

---

# 8. Hotel Booking Dataset

The current benchmark will use hotel booking data.

The main analysis is cancellation behavior.

The benchmark should distinguish between:

## Direct customers

Bookings where the customer made the booking directly.

## Agents

Bookings made through a travel agent / booking agent.

The analysis should determine cancellation rates and patterns for these groups.

Do not assume column names blindly.

Create a dataset configuration/mapping that identifies the required fields.

For example, if the dataset contains fields such as:

```text
is_canceled
agent
market_segment
```

use them appropriately.

Document the assumptions.

If the dataset uses different column names, make the mapping configurable.

---

# 9. Dataset Analysis

Before asking the LLM to analyse the data, calculate deterministic statistics using Python.

The Python analysis should establish the factual baseline.

At minimum calculate:

### Overall

* Number of bookings
* Number of cancellations
* Overall cancellation rate

### Direct customers

* Number of bookings
* Number of cancellations
* Cancellation rate

### Agent bookings

* Number of bookings
* Number of cancellations
* Cancellation rate

Also identify useful patterns available in the dataset, such as:

* hotel type
* lead time
* market segment
* deposit type
* customer type
* booking changes
* previous cancellations
* special requests
* ADR
* arrival period

Do not force analysis of columns that do not exist.

---

# 10. LLM Analysis Prompt

The LLM should receive a structured representation of the calculated dataset statistics.

Do NOT send the entire CSV to the LLM unless explicitly required.

Prefer:

```text
CSV
 |
 v
Python/Pandas
 |
 v
Statistical summary
 |
 v
LLM
 |
 v
Analysis
```

This makes the benchmark more reproducible and reduces unnecessary token usage.

The prompt should ask the LLM to analyse the hotel cancellation measurements.

The LLM should be asked to:

1. Explain the overall cancellation rate
2. Compare direct customers and agent bookings
3. Identify meaningful differences
4. Identify possible patterns
5. Explain which variables appear associated with cancellations
6. Avoid claiming causation where the data only shows correlation
7. Clearly state uncertainty
8. Base conclusions only on the supplied statistics
9. Produce a structured response

The prompt should explicitly tell the model:

> Do not invent values that are not present in the supplied data.

---

# 11. Standardised LLM Output

Where practical, request structured JSON from the LLM.

For example:

```json
{
  "summary": "...",
  "overall_cancellation": {
    "rate": 0.0,
    "interpretation": "..."
  },
  "direct_customers": {
    "rate": 0.0,
    "interpretation": "..."
  },
  "agent_bookings": {
    "rate": 0.0,
    "interpretation": "..."
  },
  "key_findings": [
    "...",
    "...",
    "..."
  ],
  "limitations": [
    "...",
    "..."
  ]
}
```

The application should validate the returned JSON.

If parsing fails:

* retain the raw response
* mark the response as invalid
* record the error
* do not crash the benchmark

---

# 12. Benchmark Metrics

For every LLM execution measure at least:

## TTFT

Time to first token.

```text
TTFT = first generated token timestamp - request start timestamp
```

## Total execution time

```text
Total time = request completion timestamp - request start timestamp
```

## Completion tokens

Use API usage information where available.

If unavailable, document the fallback method.

## Tokens/sec

Measure generated completion tokens per generation time.

Document exactly how this is calculated.

## Task pass/fail

For deterministic benchmark tasks, retain the existing pass/fail mechanism.

For hotel analysis, do not invent a simplistic pass/fail score unless a deterministic validation criterion is defined.

---

# 13. Resource Monitoring

Add resource measurements for every benchmark execution where technically possible.

Measure:

## System RAM

At minimum:

```text
RAM before
RAM after
RAM peak
```

Prefer process/system measurements that are clearly documented.

## GPU VRAM

Measure:

```text
VRAM before
VRAM after
VRAM peak
```

Support GPU measurement where available.

The implementation should gracefully handle systems where GPU monitoring is unavailable.

For example:

```text
GPU VRAM: unavailable
```

must be a valid result.

Do not pretend that GPU memory was measured if it was not.

Document which GPU monitoring mechanism is used.

For NVIDIA GPUs, a suitable implementation may use `nvidia-smi`.

Keep the resource-monitoring implementation separate from the notebook.

---

# 14. Fair Benchmarking

Make the benchmark as consistent as possible.

Use the same:

* dataset
* calculated statistics
* prompt
* temperature
* max tokens
* number of runs
* benchmark configuration

for every LLM being compared.

Record the configuration in the results.

The benchmark must make it possible to reproduce the same test.

---

# 15. Cold and Warm Runs

Keep the existing distinction between cold and warm execution.

The first request may include model-loading time.

Therefore report:

```text
Cold execution
Warm execution
```

separately where possible.

Do not mix model loading time with normal inference latency without clearly identifying it.

---

# 16. Comparison

The notebook must allow comparison of LLM responses.

For each model show:

* backend
* model
* TTFT
* total execution time
* completion tokens
* tokens/sec
* system RAM
* GPU VRAM
* response

For the hotel analysis specifically, allow the user to compare the actual LLM responses side-by-side.

Do not automatically declare one model "best".

Present the measured results and let the user make the decision.

---

# 17. Visualisations

Use Marimo and Altair for visualisation where appropriate.

Include charts such as:

### Performance

* TTFT by model
* Total execution time by model
* Tokens/sec by model

### Resource usage

* RAM usage by model
* VRAM usage by model

### Hotel cancellation

* Overall cancellation rate
* Direct vs agent cancellation rate
* Cancellation rate by relevant categorical variables

### LLM comparison

A table comparing:

```text
Model
Backend
TTFT
Total time
Tokens
Tokens/sec
RAM
VRAM
```

For LLM qualitative responses, provide readable text/JSON output rather than attempting to reduce the answer to an artificial numeric score.

---

# 18. Results Storage

Do not store benchmark results only in notebook state.

Persist them.

Prefer a structured format such as:

```text
output/results.jsonl
```

or a suitable versioned result format.

Each execution should contain enough metadata to reproduce and interpret the result.

Include:

```text
timestamp
backend
model
dataset
dataset_hash
dataset_rows
prompt/version
benchmark configuration
metrics
resource measurements
response
errors
```

Use a dataset hash so that results can be associated with the exact dataset version.

---

# 19. API Versioning

Any application API introduced by this project must be versioned.

For example:

```text
POST /api/v1/notebooks/hotel_analysis/run
```

Do not create unversioned endpoints such as:

```text
POST /api/notebooks/hotel_analysis/run
```

If no HTTP API is actually required, do not introduce one merely for the sake of having an API.

The primary interface for this project is the Marimo notebook.

---

# 20. Separation of Responsibilities

Do not put everything into the notebook.

Use modules approximately like:

```text
backends.py
    Ollama / LM Studio communication

runner.py
    LLM execution and streaming metrics

datasets.py
    CSV loading and validation

metrics.py
    Benchmark metrics

resources.py
    RAM / VRAM monitoring

analysis.py
    Hotel booking statistical analysis

models.py
    Dataclasses / result models

tasks.py
    Existing deterministic benchmark tasks

benchmark.py
    Benchmark orchestration
```

The Marimo notebook should orchestrate these components.

---

# 21. Testing

Add unit tests for the new functionality.

At minimum test:

### Dataset

* valid CSV
* empty CSV
* missing columns
* malformed data
* direct vs agent classification

### Metrics

* TTFT calculation
* total execution time
* tokens/sec
* missing token information

### Resource monitoring

* unavailable GPU
* available system RAM
* graceful failure

### LLM result parsing

* valid JSON
* invalid JSON
* incomplete response

### Analysis

* cancellation calculation
* direct customer cancellation rate
* agent cancellation rate
* empty groups
* missing values

Tests must not require a running Ollama or LM Studio server unless explicitly marked as integration tests.

---

# 22. Code Quality

Follow modern Python practices.

Use:

* Python type hints
* dataclasses or suitable typed models
* clear module responsibilities
* small functions
* meaningful names
* docstrings for public APIs
* error handling
* logging where appropriate

Avoid:

* global mutable state
* duplicated backend logic
* notebook-only business logic
* hard-coded dataset paths
* hard-coded model names
* hidden configuration
* silently ignored exceptions

---

# 23. Configuration

Configuration should be explicit.

Provide sensible defaults such as:

```text
temperature = 0
max_tokens = 1024
runs = 1
```

Allow the user to change relevant benchmark parameters in the notebook.

Record the actual configuration with every result.

---

# 24. Execution Flow

The final notebook should follow this conceptual flow:

```text
Start
  |
  v
Detect Ollama / LM Studio
  |
  v
Select backend(s)
  |
  v
Select model(s)
  |
  v
Select CSV dataset
  |
  v
Validate dataset
  |
  v
Calculate deterministic hotel statistics
  |
  v
Display dataset statistics
  |
  v
Create standardised LLM analysis prompt
  |
  v
Run selected LLMs
  |
  +--> Measure TTFT
  |
  +--> Measure total time
  |
  +--> Measure completion tokens
  |
  +--> Measure tokens/sec
  |
  +--> Measure RAM
  |
  +--> Measure VRAM
  |
  v
Validate LLM response
  |
  v
Save results
  |
  v
Compare performance
  |
  v
Compare hotel analysis responses
  |
  v
Display results
  |
  v
Export results
```

---

# 25. Important Development Rule

Do not blindly implement the specification.

First inspect the existing source code and identify what is already implemented.

For each requested feature, classify it as:

```text
ALREADY IMPLEMENTED
EXTEND EXISTING
NEW COMPONENT
REFACTOR REQUIRED
NOT REQUIRED
```

Avoid unnecessary rewrites.

Preserve backwards compatibility with existing benchmark functionality where practical.

---

# 26. Implementation Order

Follow this exact order:

## Step 1

Inspect the existing repository and uploaded source files.

## Step 2

Produce the architecture and implementation plan.

## Step 3

Create/update:

```text
README.md
ARCHITECTURE.md
BENCHMARK_METHODOLOGY.md
```

## Step 4

Design the data/result models.

## Step 5

Implement dataset loading and validation.

## Step 6

Implement deterministic hotel cancellation analysis.

## Step 7

Implement resource monitoring.

## Step 8

Extend the existing benchmark runner.

## Step 9

Implement structured LLM analysis prompts and response validation.

## Step 10

Implement result persistence.

## Step 11

Create the Marimo notebook.

## Step 12

Add visualisations.

## Step 13

Add tests.

## Step 14

Run the tests.

## Step 15

Run static checks/linting if configured.

## Step 16

Run the notebook with a test dataset if available.

## Step 17

Review the implementation against this specification.

## Step 18

Update the README with the final actual behavior.

---

# 27. Final Verification

Before declaring the work complete, verify:

* [ ] Notebook is under `./notebooks`
* [ ] Backend code is under `./src`
* [ ] Existing Ollama support works
* [ ] Existing LM Studio support works
* [ ] Models can be selected from the notebook
* [ ] CSV can be selected from the notebook
* [ ] Dataset validation works
* [ ] Hotel cancellation statistics are calculated by Python
* [ ] Direct customers are analysed separately
* [ ] Agent bookings are analysed separately
* [ ] LLM receives deterministic statistics
* [ ] LLM responses are captured
* [ ] TTFT is measured
* [ ] Total execution time is measured
* [ ] Completion tokens are measured
* [ ] Tokens/sec is measured
* [ ] RAM is measured where possible
* [ ] GPU VRAM is measured where possible
* [ ] Missing GPU monitoring does not crash the benchmark
* [ ] Results are persisted
* [ ] Results contain sufficient metadata
* [ ] LLM responses can be compared
* [ ] Tests pass
* [ ] Documentation matches the implementation
* [ ] No unsupported performance or quality claims are made
* [ ] No model is automatically declared the "best"

At the end, provide a concise implementation summary containing:

1. Files created
2. Files modified
3. Major architectural changes
4. New benchmark metrics
5. Dataset analysis functionality
6. Resource monitoring functionality
7. Tests added
8. How to run the benchmark
9. Any limitations or assumptions

Do not skip the planning and artifact phases.
